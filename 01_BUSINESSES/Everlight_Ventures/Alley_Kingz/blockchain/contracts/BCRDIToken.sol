// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

/**
 * @title BCRDIToken
 * @dev $BCRDI - The native token for Alley Kingz on Zilliqa EVM
 *
 * Total Supply: 100,000,000 BCRDI
 * Distribution:
 *   30% Play-to-Earn rewards (GameVault)
 *   20% Team/dev treasury (12-month cliff, 36-month vest)
 *   15% Liquidity provision (ZilSwap BCRDI/ZIL)
 *   15% Staking rewards pool
 *   10% Marketing, airdrops, community
 *    5% Presale
 *    5% Advisors/partners
 *
 * The game IS the burn engine:
 *   - Card upgrades burn $BCRDI
 *   - Marketplace fees (2.5%) burned
 *   - Tournament entry fees burned
 *   - Scheduled treasury burns (~833K/month for 12 months)
 */
contract BCRDIToken is ERC20, ERC20Burnable, Ownable, ERC20Permit {
    uint256 public constant MAX_SUPPLY = 100_000_000 * 10 ** 18;

    // Allocation tracking
    uint256 public constant P2E_ALLOCATION = 30_000_000 * 10 ** 18;
    uint256 public constant TEAM_ALLOCATION = 20_000_000 * 10 ** 18;
    uint256 public constant LIQUIDITY_ALLOCATION = 15_000_000 * 10 ** 18;
    uint256 public constant STAKING_ALLOCATION = 15_000_000 * 10 ** 18;
    uint256 public constant MARKETING_ALLOCATION = 10_000_000 * 10 ** 18;
    uint256 public constant PRESALE_ALLOCATION = 5_000_000 * 10 ** 18;
    uint256 public constant ADVISOR_ALLOCATION = 5_000_000 * 10 ** 18;

    // Vesting
    uint256 public teamCliffEnd;
    uint256 public teamVestEnd;
    uint256 public teamWithdrawn;
    address public teamWallet;

    // Game integration
    mapping(address => bool) public gameContracts;
    uint256 public totalBurnedByGame;

    // Presale
    bool public presaleActive;
    uint256 public presaleRate; // BCRDI per ZIL (in wei)
    uint256 public presaleSold;
    uint256 public presaleHardCap;

    event GameContractUpdated(address indexed contractAddr, bool authorized);
    event GameBurn(address indexed from, uint256 amount, string reason);
    event PresalePurchase(address indexed buyer, uint256 zilAmount, uint256 bcrdiAmount);

    constructor(
        address _teamWallet
    ) ERC20("BCRDI Token", "BCRDI") Ownable(msg.sender) ERC20Permit("BCRDI Token") {
        require(_teamWallet != address(0), "Invalid team wallet");
        teamWallet = _teamWallet;

        // Vesting: 12-month cliff, 36-month total vest
        teamCliffEnd = block.timestamp + 365 days;
        teamVestEnd = block.timestamp + (365 days * 3);

        // Mint allocations (except team which vests)
        _mint(msg.sender, LIQUIDITY_ALLOCATION); // Owner provides LP
        _mint(msg.sender, MARKETING_ALLOCATION); // Marketing wallet
        _mint(msg.sender, ADVISOR_ALLOCATION);   // Advisor distribution
        _mint(address(this), PRESALE_ALLOCATION); // Held for presale
        // P2E + Staking minted to GameVault/Staking contracts after deployment
        // Team allocation minted on vest schedule
    }

    // --- Game Integration ---

    /// @notice Authorize a game contract to trigger burns
    function setGameContract(address contractAddr, bool authorized) external onlyOwner {
        gameContracts[contractAddr] = authorized;
        emit GameContractUpdated(contractAddr, authorized);
    }

    /// @notice Burn tokens for in-game actions (card upgrades, tournament fees, etc.)
    function gameBurn(address from, uint256 amount, string calldata reason) external {
        require(gameContracts[msg.sender], "Not authorized game contract");
        _burn(from, amount);
        totalBurnedByGame += amount;
        emit GameBurn(from, amount, reason);
    }

    // --- Presale ---

    /// @notice Start the presale with a rate and hard cap
    function startPresale(uint256 _rate, uint256 _hardCap) external onlyOwner {
        require(!presaleActive, "Presale already active");
        require(_rate > 0, "Invalid rate");
        presaleRate = _rate;
        presaleHardCap = _hardCap;
        presaleActive = true;
    }

    /// @notice Buy $BCRDI in presale with ZIL
    function buyPresale() external payable {
        require(presaleActive, "Presale not active");
        require(msg.value > 0, "Send ZIL");

        uint256 bcrdiAmount = (msg.value * presaleRate) / 1e18;
        require(presaleSold + bcrdiAmount <= PRESALE_ALLOCATION, "Presale sold out");
        require(
            presaleHardCap == 0 || address(this).balance <= presaleHardCap,
            "Hard cap reached"
        );

        presaleSold += bcrdiAmount;
        _transfer(address(this), msg.sender, bcrdiAmount);
        emit PresalePurchase(msg.sender, msg.value, bcrdiAmount);
    }

    /// @notice End presale and lock LP
    function endPresale() external onlyOwner {
        presaleActive = false;
    }

    // --- Team Vesting ---

    /// @notice Mint vested team tokens (after cliff, linear over 36 months)
    function claimTeamTokens() external {
        require(msg.sender == teamWallet, "Not team wallet");
        require(block.timestamp >= teamCliffEnd, "Cliff not reached");

        uint256 elapsed = block.timestamp - teamCliffEnd;
        uint256 vestDuration = teamVestEnd - teamCliffEnd;
        uint256 totalVested;

        if (elapsed >= vestDuration) {
            totalVested = TEAM_ALLOCATION;
        } else {
            totalVested = (TEAM_ALLOCATION * elapsed) / vestDuration;
        }

        uint256 claimable = totalVested - teamWithdrawn;
        require(claimable > 0, "Nothing to claim");

        teamWithdrawn += claimable;
        _mint(teamWallet, claimable);
    }

    // --- Minting for Game Contracts ---

    /// @notice Mint P2E rewards to the GameVault contract
    function mintToGameVault(address vault, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(vault, amount);
    }

    /// @notice Mint staking rewards to the Staking contract
    function mintToStaking(address stakingContract, uint256 amount) external onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(stakingContract, amount);
    }

    // --- Admin ---

    /// @notice Withdraw presale ZIL (for LP provision)
    function withdrawPresaleFunds(address payable to) external onlyOwner {
        require(!presaleActive, "End presale first");
        uint256 balance = address(this).balance;
        require(balance > 0, "No funds");
        to.transfer(balance);
    }

    /// @notice Update team wallet address
    function updateTeamWallet(address newWallet) external {
        require(msg.sender == teamWallet, "Not team wallet");
        require(newWallet != address(0), "Invalid address");
        teamWallet = newWallet;
    }

    receive() external payable {}
}
