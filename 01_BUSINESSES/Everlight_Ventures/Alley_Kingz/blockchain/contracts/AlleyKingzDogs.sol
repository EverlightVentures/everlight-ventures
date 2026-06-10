// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title AlleyKingzDogs
 * @dev ERC-721 companion Dog NFTs -- ride shotgun in your cars during battle
 *
 * Each dog is unique with breed, rarity tier, and cosmetic traits.
 * Airdropped to: $BCRDI stakers, ranked finishers, tournament winners,
 * early adopters (Genesis Dogs), community events.
 *
 * Dogs provide cosmetic buffs (NOT pay-to-win):
 *   - Custom deploy animation
 *   - Victory celebration animation
 *   - Profile badge/frame
 *
 * Featured breed: Dogo Argentino "$BCARDD" (the OG mascot, Mythic tier)
 */
contract AlleyKingzDogs is ERC721, ERC721Enumerable, Ownable {
    uint256 private _nextTokenId = 1;
    string private _baseTokenURI;

    // Dog metadata
    struct DogMeta {
        string breed;         // e.g. "Dogo Argentino", "Pit Bull", "Rottweiler"
        uint8 rarity;         // 0=Common, 1=Rare, 2=Epic, 3=Legendary, 4=Mythic
        string trait1;        // Cosmetic trait (e.g. "Gold Chain", "Bandana")
        string trait2;        // Cosmetic trait (e.g. "Sunglasses", "Scar")
        uint256 mintedAt;     // Timestamp
        bool isGenesis;       // Genesis drop -- first 10,000
    }

    mapping(uint256 => DogMeta) public dogs;

    // Breed registry
    struct BreedInfo {
        string breedName;
        uint8 defaultRarity;
        uint256 maxSupply;    // 0 = unlimited
        uint256 minted;
    }

    mapping(uint256 => BreedInfo) public breeds;
    uint256 public nextBreedId = 1;

    // Authorized minters (AirdropManager, StakingContract, etc.)
    mapping(address => bool) public authorizedMinters;

    // Genesis tracking
    uint256 public constant GENESIS_CAP = 10_000;
    uint256 public genesisMinted;
    bool public genesisComplete;

    // Royalties
    address public royaltyReceiver;
    uint96 public constant ROYALTY_BPS = 250; // 2.5%

    event DogMinted(uint256 indexed tokenId, address indexed to, string breed, uint8 rarity, bool isGenesis);
    event BreedRegistered(uint256 indexed breedId, string breedName, uint8 rarity);
    event AirdropBatch(address[] recipients, uint256[] tokenIds);

    constructor(
        string memory baseUri,
        address _royaltyReceiver
    ) ERC721("Alley Kingz Dogs", "AKD") Ownable(msg.sender) {
        _baseTokenURI = baseUri;
        royaltyReceiver = _royaltyReceiver;

        // Register the OG breed
        _registerBreed("Dogo Argentino", 4, 100); // Mythic, max 100
        _registerBreed("Pit Bull", 2, 0);          // Epic, unlimited
        _registerBreed("Rottweiler", 2, 0);         // Epic, unlimited
        _registerBreed("German Shepherd", 1, 0);    // Rare, unlimited
        _registerBreed("Doberman", 1, 0);           // Rare, unlimited
        _registerBreed("Bulldog", 0, 0);            // Common, unlimited
        _registerBreed("Husky", 1, 0);              // Rare, unlimited
        _registerBreed("Great Dane", 2, 0);         // Epic, unlimited
        _registerBreed("Cane Corso", 3, 500);       // Legendary, max 500
        _registerBreed("Belgian Malinois", 3, 500); // Legendary, max 500
    }

    // --- Breed Management ---

    function _registerBreed(
        string memory breedName,
        uint8 defaultRarity,
        uint256 maxSupply
    ) internal returns (uint256) {
        uint256 breedId = nextBreedId++;
        breeds[breedId] = BreedInfo({
            breedName: breedName,
            defaultRarity: defaultRarity,
            maxSupply: maxSupply,
            minted: 0
        });
        emit BreedRegistered(breedId, breedName, defaultRarity);
        return breedId;
    }

    function registerBreed(
        string calldata breedName,
        uint8 defaultRarity,
        uint256 maxSupply
    ) external onlyOwner returns (uint256) {
        return _registerBreed(breedName, defaultRarity, maxSupply);
    }

    // --- Minting ---

    function setAuthorizedMinter(address minter, bool authorized) external onlyOwner {
        authorizedMinters[minter] = authorized;
    }

    /// @notice Mint a single dog NFT
    function mintDog(
        address to,
        uint256 breedId,
        string calldata trait1,
        string calldata trait2
    ) external returns (uint256) {
        require(authorizedMinters[msg.sender] || msg.sender == owner(), "Not authorized");
        require(breedId > 0 && breedId < nextBreedId, "Invalid breed");

        BreedInfo storage breed = breeds[breedId];
        if (breed.maxSupply > 0) {
            require(breed.minted < breed.maxSupply, "Breed supply exhausted");
        }
        breed.minted++;

        uint256 tokenId = _nextTokenId++;
        bool genesis = !genesisComplete && genesisMinted < GENESIS_CAP;
        if (genesis) {
            genesisMinted++;
            if (genesisMinted >= GENESIS_CAP) {
                genesisComplete = true;
            }
        }

        dogs[tokenId] = DogMeta({
            breed: breed.breedName,
            rarity: breed.defaultRarity,
            trait1: trait1,
            trait2: trait2,
            mintedAt: block.timestamp,
            isGenesis: genesis
        });

        _safeMint(to, tokenId);
        emit DogMinted(tokenId, to, breed.breedName, breed.defaultRarity, genesis);
        return tokenId;
    }

    /// @notice Batch airdrop dogs to multiple recipients
    function airdropBatch(
        address[] calldata recipients,
        uint256[] calldata breedIds,
        string[] calldata traits1,
        string[] calldata traits2
    ) external onlyOwner {
        require(recipients.length == breedIds.length, "Length mismatch");
        uint256[] memory tokenIds = new uint256[](recipients.length);

        for (uint256 i = 0; i < recipients.length; i++) {
            BreedInfo storage breed = breeds[breedIds[i]];
            if (breed.maxSupply > 0) {
                require(breed.minted < breed.maxSupply, "Breed supply exhausted");
            }
            breed.minted++;

            uint256 tokenId = _nextTokenId++;
            bool genesis = !genesisComplete && genesisMinted < GENESIS_CAP;
            if (genesis) {
                genesisMinted++;
                if (genesisMinted >= GENESIS_CAP) {
                    genesisComplete = true;
                }
            }

            dogs[tokenId] = DogMeta({
                breed: breed.breedName,
                rarity: breed.defaultRarity,
                trait1: traits1[i],
                trait2: traits2[i],
                mintedAt: block.timestamp,
                isGenesis: genesis
            });

            _safeMint(recipients[i], tokenId);
            tokenIds[i] = tokenId;
        }
        emit AirdropBatch(recipients, tokenIds);
    }

    // --- Views ---

    function getDog(uint256 tokenId) external view returns (DogMeta memory) {
        require(_ownerOf(tokenId) != address(0), "Dog does not exist");
        return dogs[tokenId];
    }

    function getBreed(uint256 breedId) external view returns (BreedInfo memory) {
        return breeds[breedId];
    }

    function totalBreeds() external view returns (uint256) {
        return nextBreedId - 1;
    }

    // --- Royalties (EIP-2981) ---

    function royaltyInfo(
        uint256,
        uint256 salePrice
    ) external view returns (address, uint256) {
        return (royaltyReceiver, (salePrice * ROYALTY_BPS) / 10000);
    }

    function setRoyaltyReceiver(address newReceiver) external onlyOwner {
        royaltyReceiver = newReceiver;
    }

    // --- URI ---

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    function setBaseURI(string calldata newBaseURI) external onlyOwner {
        _baseTokenURI = newBaseURI;
    }

    // --- Overrides ---

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Enumerable) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(
        address account,
        uint128 value
    ) internal override(ERC721, ERC721Enumerable) {
        super._increaseBalance(account, value);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, ERC721Enumerable) returns (bool) {
        return interfaceId == 0x2a55205a || super.supportsInterface(interfaceId);
    }
}
