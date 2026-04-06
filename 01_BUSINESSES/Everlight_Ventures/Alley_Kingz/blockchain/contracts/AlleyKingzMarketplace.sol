// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC1155/IERC1155.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";
import "@openzeppelin/contracts/token/ERC721/utils/ERC721Holder.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title AlleyKingzMarketplace
 * @dev P2P NFT marketplace for Alley Kingz
 *
 * Trade Car NFTs (ERC-1155) and Dog NFTs (ERC-721) for $BCRDI.
 * 2.5% fee on every sale -- burned (deflationary pressure on $BCRDI).
 *
 * Supports:
 *   - Fixed price listings
 *   - Batch listings
 *   - Listing cancellation
 *   - Royalty enforcement (2.5% to creator on secondary)
 */
contract AlleyKingzMarketplace is Ownable, ReentrancyGuard, ERC1155Holder, ERC721Holder {
    using SafeERC20 for IERC20;

    IERC20 public bcrdiToken;
    address public cardsContract;  // ERC-1155
    address public dogsContract;   // ERC-721

    // Fee: 2.5% burned
    uint256 public constant FEE_BPS = 250;
    // Royalty: 2.5% to creator
    uint256 public constant ROYALTY_BPS = 250;
    address public royaltyReceiver;

    uint256 public totalVolume;
    uint256 public totalBurned;
    uint256 public nextListingId = 1;

    enum ListingType { ERC1155, ERC721 }

    struct Listing {
        uint256 listingId;
        address seller;
        ListingType listingType;
        uint256 tokenId;
        uint256 amount;         // For ERC-1155 (always 1 for ERC-721)
        uint256 pricePerUnit;   // In $BCRDI (wei)
        bool active;
        uint256 listedAt;
    }

    mapping(uint256 => Listing) public listings;

    // Index: seller => their listing IDs
    mapping(address => uint256[]) public sellerListings;

    event Listed(
        uint256 indexed listingId,
        address indexed seller,
        ListingType listingType,
        uint256 tokenId,
        uint256 amount,
        uint256 pricePerUnit
    );
    event Sold(
        uint256 indexed listingId,
        address indexed buyer,
        address indexed seller,
        uint256 totalPrice,
        uint256 feeBurned,
        uint256 royaltyPaid
    );
    event Cancelled(uint256 indexed listingId);

    constructor(
        address _bcrdiToken,
        address _cardsContract,
        address _dogsContract,
        address _royaltyReceiver
    ) Ownable(msg.sender) {
        bcrdiToken = IERC20(_bcrdiToken);
        cardsContract = _cardsContract;
        dogsContract = _dogsContract;
        royaltyReceiver = _royaltyReceiver;
    }

    // --- Listing ---

    /// @notice List Car NFTs (ERC-1155) for sale
    function listCards(
        uint256 tokenId,
        uint256 amount,
        uint256 pricePerUnit
    ) external nonReentrant returns (uint256) {
        require(amount > 0 && pricePerUnit > 0, "Invalid params");

        // Transfer cards to marketplace (escrow)
        IERC1155(cardsContract).safeTransferFrom(msg.sender, address(this), tokenId, amount, "");

        uint256 listingId = nextListingId++;
        listings[listingId] = Listing({
            listingId: listingId,
            seller: msg.sender,
            listingType: ListingType.ERC1155,
            tokenId: tokenId,
            amount: amount,
            pricePerUnit: pricePerUnit,
            active: true,
            listedAt: block.timestamp
        });

        sellerListings[msg.sender].push(listingId);
        emit Listed(listingId, msg.sender, ListingType.ERC1155, tokenId, amount, pricePerUnit);
        return listingId;
    }

    /// @notice List a Dog NFT (ERC-721) for sale
    function listDog(
        uint256 tokenId,
        uint256 price
    ) external nonReentrant returns (uint256) {
        require(price > 0, "Invalid price");

        // Transfer dog to marketplace (escrow)
        IERC721(dogsContract).safeTransferFrom(msg.sender, address(this), tokenId);

        uint256 listingId = nextListingId++;
        listings[listingId] = Listing({
            listingId: listingId,
            seller: msg.sender,
            listingType: ListingType.ERC721,
            tokenId: tokenId,
            amount: 1,
            pricePerUnit: price,
            active: true,
            listedAt: block.timestamp
        });

        sellerListings[msg.sender].push(listingId);
        emit Listed(listingId, msg.sender, ListingType.ERC721, tokenId, 1, price);
        return listingId;
    }

    // --- Buying ---

    /// @notice Buy a listed NFT (cards or dog)
    function buy(uint256 listingId, uint256 quantity) external nonReentrant {
        Listing storage listing = listings[listingId];
        require(listing.active, "Not active");
        require(listing.seller != msg.sender, "Cannot buy own listing");

        uint256 buyAmount = listing.listingType == ListingType.ERC721 ? 1 : quantity;
        require(buyAmount > 0 && buyAmount <= listing.amount, "Invalid quantity");

        uint256 totalPrice = listing.pricePerUnit * buyAmount;

        // Calculate fees
        uint256 fee = (totalPrice * FEE_BPS) / 10000;       // 2.5% burned
        uint256 royalty = (totalPrice * ROYALTY_BPS) / 10000; // 2.5% to creator
        uint256 sellerReceives = totalPrice - fee - royalty;

        // Transfer $BCRDI from buyer
        bcrdiToken.safeTransferFrom(msg.sender, listing.seller, sellerReceives);
        bcrdiToken.safeTransferFrom(msg.sender, royaltyReceiver, royalty);

        // Burn the fee (transfer to dead address or call burn if available)
        bcrdiToken.safeTransferFrom(msg.sender, address(0xdead), fee);
        totalBurned += fee;

        // Transfer NFT to buyer
        if (listing.listingType == ListingType.ERC1155) {
            IERC1155(cardsContract).safeTransferFrom(
                address(this), msg.sender, listing.tokenId, buyAmount, ""
            );
            listing.amount -= buyAmount;
            if (listing.amount == 0) {
                listing.active = false;
            }
        } else {
            IERC721(dogsContract).safeTransferFrom(
                address(this), msg.sender, listing.tokenId
            );
            listing.active = false;
        }

        totalVolume += totalPrice;
        emit Sold(listingId, msg.sender, listing.seller, totalPrice, fee, royalty);
    }

    // --- Cancellation ---

    /// @notice Cancel a listing and return NFTs to seller
    function cancel(uint256 listingId) external nonReentrant {
        Listing storage listing = listings[listingId];
        require(listing.active, "Not active");
        require(listing.seller == msg.sender || msg.sender == owner(), "Not authorized");

        listing.active = false;

        // Return NFT
        if (listing.listingType == ListingType.ERC1155) {
            IERC1155(cardsContract).safeTransferFrom(
                address(this), listing.seller, listing.tokenId, listing.amount, ""
            );
        } else {
            IERC721(dogsContract).safeTransferFrom(
                address(this), listing.seller, listing.tokenId
            );
        }

        emit Cancelled(listingId);
    }

    // --- View Functions ---

    function getListing(uint256 listingId) external view returns (Listing memory) {
        return listings[listingId];
    }

    function getSellerListings(address seller) external view returns (uint256[] memory) {
        return sellerListings[seller];
    }

    function totalListings() external view returns (uint256) {
        return nextListingId - 1;
    }

    // --- Admin ---

    function setRoyaltyReceiver(address newReceiver) external onlyOwner {
        royaltyReceiver = newReceiver;
    }

    function updateContracts(address _cards, address _dogs) external onlyOwner {
        if (_cards != address(0)) cardsContract = _cards;
        if (_dogs != address(0)) dogsContract = _dogs;
    }
}
