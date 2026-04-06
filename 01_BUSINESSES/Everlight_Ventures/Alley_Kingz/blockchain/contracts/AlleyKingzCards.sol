// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";

/**
 * @title AlleyKingzCards
 * @dev ERC-1155 NFT contract for game cards (dogs driving cars)
 *
 * Each card type = token ID. Players can own multiple copies.
 * Supports batch minting for pack openings.
 * 2.5% royalty on secondary sales.
 *
 * Card types: Troops, Spells, Buildings, Vehicles, Champions
 * Rarities: Common (0), Rare (1), Epic (2), Legendary (3), Mythic (4)
 */
contract AlleyKingzCards is ERC1155, Ownable, ERC1155Supply {
    string public name = "Alley Kingz Cards";
    string public symbol = "AKC";

    // Royalty info (EIP-2981)
    address public royaltyReceiver;
    uint96 public constant ROYALTY_BPS = 250; // 2.5%

    // Card metadata
    struct CardMeta {
        string cardName;      // e.g. "Bacardi - Dogo Argentino"
        uint8 rarity;         // 0=Common, 1=Rare, 2=Epic, 3=Legendary, 4=Mythic
        uint8 cardType;       // 0=Troop, 1=Spell, 2=Building, 3=Vehicle, 4=Champion
        uint8 elixirCost;     // 1-10
        string breed;         // Dog breed for the driver
        uint256 maxSupply;    // 0 = unlimited, >0 = limited edition
        bool active;          // Can be minted
    }

    mapping(uint256 => CardMeta) public cards;
    uint256 public nextCardId = 1;

    // Authorized minters (GameVault, PackOpener, etc.)
    mapping(address => bool) public authorizedMinters;

    // Genesis tracking
    bool public genesisLocked;
    mapping(uint256 => bool) public isGenesis;

    event CardCreated(uint256 indexed cardId, string cardName, uint8 rarity, string breed);
    event PackOpened(address indexed player, uint256[] cardIds, uint256[] amounts);
    event CardBurned(address indexed player, uint256 indexed cardId, uint256 amount);

    constructor(
        string memory baseUri,
        address _royaltyReceiver
    ) ERC1155(baseUri) Ownable(msg.sender) {
        royaltyReceiver = _royaltyReceiver;
    }

    // --- Card Registration ---

    /// @notice Register a new card type
    function createCard(
        string calldata cardName,
        uint8 rarity,
        uint8 cardType,
        uint8 elixirCost,
        string calldata breed,
        uint256 maxSupply
    ) external onlyOwner returns (uint256) {
        uint256 cardId = nextCardId++;
        cards[cardId] = CardMeta({
            cardName: cardName,
            rarity: rarity,
            cardType: cardType,
            elixirCost: elixirCost,
            breed: breed,
            maxSupply: maxSupply,
            active: true
        });
        emit CardCreated(cardId, cardName, rarity, breed);
        return cardId;
    }

    /// @notice Register multiple cards at once (calls createCard in loop)
    function createCardBatch(
        string[] calldata cardNames,
        uint8[] calldata rarities,
        uint8[] calldata cardTypes,
        uint8[] calldata elixirCosts,
        string[] calldata breeds,
        uint256[] calldata maxSupplies
    ) external onlyOwner returns (uint256[] memory) {
        require(cardNames.length == rarities.length, "Length mismatch");
        uint256[] memory ids = new uint256[](cardNames.length);
        for (uint256 i = 0; i < cardNames.length; i++) {
            ids[i] = _createCard(cardNames[i], rarities[i], cardTypes[i], elixirCosts[i], breeds[i], maxSupplies[i]);
        }
        return ids;
    }

    function _createCard(
        string calldata cardName,
        uint8 rarity,
        uint8 cardType,
        uint8 elixirCost,
        string calldata breed,
        uint256 maxSupply
    ) internal returns (uint256) {
        uint256 cardId = nextCardId++;
        cards[cardId] = CardMeta(cardName, rarity, cardType, elixirCost, breed, maxSupply, true);
        emit CardCreated(cardId, cardName, rarity, breed);
        return cardId;
    }

    /// @notice Mark cards as Genesis edition (can never be minted again after lock)
    function markGenesis(uint256[] calldata cardIds) external onlyOwner {
        require(!genesisLocked, "Genesis already locked");
        for (uint256 i = 0; i < cardIds.length; i++) {
            isGenesis[cardIds[i]] = true;
        }
    }

    /// @notice Lock genesis cards permanently (no more genesis minting)
    function lockGenesis() external onlyOwner {
        genesisLocked = true;
    }

    // --- Minting ---

    /// @notice Authorize a contract to mint cards (PackOpener, GameVault, etc.)
    function setAuthorizedMinter(address minter, bool authorized) external onlyOwner {
        authorizedMinters[minter] = authorized;
    }

    /// @notice Mint a single card to a player
    function mint(address to, uint256 cardId, uint256 amount) external {
        require(authorizedMinters[msg.sender] || msg.sender == owner(), "Not authorized");
        require(cards[cardId].active, "Card not active");
        if (genesisLocked && isGenesis[cardId]) {
            revert("Genesis cards locked");
        }
        if (cards[cardId].maxSupply > 0) {
            require(
                totalSupply(cardId) + amount <= cards[cardId].maxSupply,
                "Exceeds max supply"
            );
        }
        _mint(to, cardId, amount, "");
    }

    /// @notice Mint a pack of cards to a player (batch)
    function mintPack(
        address to,
        uint256[] calldata cardIds,
        uint256[] calldata amounts
    ) external {
        require(authorizedMinters[msg.sender] || msg.sender == owner(), "Not authorized");
        for (uint256 i = 0; i < cardIds.length; i++) {
            require(cards[cardIds[i]].active, "Card not active");
            if (genesisLocked && isGenesis[cardIds[i]]) {
                revert("Genesis cards locked");
            }
            if (cards[cardIds[i]].maxSupply > 0) {
                require(
                    totalSupply(cardIds[i]) + amounts[i] <= cards[cardIds[i]].maxSupply,
                    "Exceeds max supply"
                );
            }
        }
        _mintBatch(to, cardIds, amounts, "");
        emit PackOpened(to, cardIds, amounts);
    }

    // --- Burning (for card upgrades) ---

    /// @notice Burn cards (used for upgrades -- burns duplicate NFTs)
    function burnForUpgrade(
        address from,
        uint256 cardId,
        uint256 amount
    ) external {
        require(authorizedMinters[msg.sender] || msg.sender == owner(), "Not authorized");
        _burn(from, cardId, amount);
        emit CardBurned(from, cardId, amount);
    }

    // --- Card Management ---

    /// @notice Deactivate a card (can't be minted anymore)
    function setCardActive(uint256 cardId, bool active) external onlyOwner {
        cards[cardId].active = active;
    }

    /// @notice Update base URI for metadata
    function setURI(string memory newUri) external onlyOwner {
        _setURI(newUri);
    }

    // --- Royalties (EIP-2981) ---

    function royaltyInfo(
        uint256,
        uint256 salePrice
    ) external view returns (address, uint256) {
        uint256 royaltyAmount = (salePrice * ROYALTY_BPS) / 10000;
        return (royaltyReceiver, royaltyAmount);
    }

    function setRoyaltyReceiver(address newReceiver) external onlyOwner {
        royaltyReceiver = newReceiver;
    }

    // --- View Functions ---

    function getCard(uint256 cardId) external view returns (CardMeta memory) {
        return cards[cardId];
    }

    function totalCards() external view returns (uint256) {
        return nextCardId - 1;
    }

    // --- Overrides ---

    function _update(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory values
    ) internal override(ERC1155, ERC1155Supply) {
        super._update(from, to, ids, values);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC1155) returns (bool) {
        // EIP-2981 interface ID
        return interfaceId == 0x2a55205a || super.supportsInterface(interfaceId);
    }
}
