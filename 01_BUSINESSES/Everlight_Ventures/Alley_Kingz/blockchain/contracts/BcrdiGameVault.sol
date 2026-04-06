// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title BcrdiGameVault
 * @dev Holds and distributes $BCRDI Play-to-Earn rewards
 *
 * 30M $BCRDI allocated for P2E, distributed over 5 years with seasonal halving.
 * Game server calls distributeReward() after each battle win.
 * Rewards scale by arena level (higher arena = more $BCRDI per win).
 *
 * Anti-abuse:
 *   - Daily per-player cap
 *   - Authorized game server only
 *   - Season halving reduces emissions over time
 */
contract BcrdiGameVault is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public bcrdiToken;

    // Season tracking
    uint256 public currentSeason;
    uint256 public seasonStartTime;
    uint256 public constant SEASON_DURATION = 35 days; // Crew Pass cycle

    // Halving: each season reduces max payout by this factor (in basis points)
    // 9500 = 95% of previous season (5% reduction per season)
    uint256 public halvingFactorBps = 9500;
    uint256 public baseRewardPerWin = 10 * 1e18; // 10 BCRDI base (Arena 1)

    // Per-player daily limits
    uint256 public maxDailyRewardPerPlayer = 500 * 1e18; // 500 BCRDI/day max
    mapping(address => mapping(uint256 => uint256)) public dailyRewards; // player => day => amount

    // Authorized game servers
    mapping(address => bool) public gameServers;

    // Stats
    uint256 public totalDistributed;
    uint256 public totalPlayers;
    mapping(address => uint256) public playerTotalEarned;
    mapping(address => bool) private knownPlayer;

    event RewardDistributed(address indexed player, uint256 amount, uint256 arena, uint256 season);
    event SeasonAdvanced(uint256 newSeason, uint256 newBaseReward);
    event GameServerUpdated(address indexed server, bool authorized);

    constructor(address _bcrdiToken) Ownable(msg.sender) {
        bcrdiToken = IERC20(_bcrdiToken);
        currentSeason = 1;
        seasonStartTime = block.timestamp;
    }

    // --- Game Server Management ---

    function setGameServer(address server, bool authorized) external onlyOwner {
        gameServers[server] = authorized;
        emit GameServerUpdated(server, authorized);
    }

    // --- Reward Distribution ---

    /// @notice Distribute reward to a player after winning a battle
    /// @param player The winner's address
    /// @param arenaLevel 1-32, scales the reward
    function distributeReward(
        address player,
        uint256 arenaLevel
    ) external nonReentrant {
        require(gameServers[msg.sender], "Not authorized game server");
        require(player != address(0), "Invalid player");
        require(arenaLevel >= 1 && arenaLevel <= 32, "Invalid arena");

        // Check if season needs advancing
        _checkSeason();

        // Calculate reward with arena scaling and season halving
        uint256 reward = _calculateReward(arenaLevel);

        // Check daily cap
        uint256 today = block.timestamp / 1 days;
        require(
            dailyRewards[player][today] + reward <= maxDailyRewardPerPlayer,
            "Daily cap reached"
        );

        // Check vault has enough tokens
        uint256 balance = bcrdiToken.balanceOf(address(this));
        require(balance >= reward, "Vault depleted");

        // Distribute
        dailyRewards[player][today] += reward;
        totalDistributed += reward;

        if (!knownPlayer[player]) {
            knownPlayer[player] = true;
            totalPlayers++;
        }
        playerTotalEarned[player] += reward;

        bcrdiToken.safeTransfer(player, reward);
        emit RewardDistributed(player, reward, arenaLevel, currentSeason);
    }

    /// @notice Calculate reward based on arena and season
    function _calculateReward(uint256 arenaLevel) internal view returns (uint256) {
        // Arena scaling: Arena 1 = base, Arena 32 = ~7.5x base
        // Uses the arena chart from the plan
        uint256 arenaMultiplier;
        if (arenaLevel <= 8) {
            arenaMultiplier = arenaLevel; // 1-8x
        } else if (arenaLevel <= 16) {
            arenaMultiplier = 8 + (arenaLevel - 8) * 2; // 10-24x
        } else if (arenaLevel <= 24) {
            arenaMultiplier = 24 + (arenaLevel - 16) * 3; // 27-48x
        } else {
            arenaMultiplier = 48 + (arenaLevel - 24) * 4; // 52-80x
        }

        uint256 seasonReward = baseRewardPerWin;
        // Apply halving for each season past the first
        for (uint256 s = 1; s < currentSeason; s++) {
            seasonReward = (seasonReward * halvingFactorBps) / 10000;
        }

        return (seasonReward * arenaMultiplier) / 10;
    }

    /// @notice Auto-advance season if duration elapsed
    function _checkSeason() internal {
        if (block.timestamp >= seasonStartTime + SEASON_DURATION) {
            uint256 elapsed = block.timestamp - seasonStartTime;
            uint256 seasonsElapsed = elapsed / SEASON_DURATION;
            currentSeason += seasonsElapsed;
            seasonStartTime += seasonsElapsed * SEASON_DURATION;
            emit SeasonAdvanced(currentSeason, _calculateReward(1));
        }
    }

    // --- View Functions ---

    /// @notice Preview reward for an arena level
    function previewReward(uint256 arenaLevel) external view returns (uint256) {
        return _calculateReward(arenaLevel);
    }

    /// @notice Check remaining daily allowance for a player
    function dailyAllowanceRemaining(address player) external view returns (uint256) {
        uint256 today = block.timestamp / 1 days;
        uint256 used = dailyRewards[player][today];
        if (used >= maxDailyRewardPerPlayer) return 0;
        return maxDailyRewardPerPlayer - used;
    }

    /// @notice Vault balance
    function vaultBalance() external view returns (uint256) {
        return bcrdiToken.balanceOf(address(this));
    }

    // --- Admin ---

    function setMaxDailyReward(uint256 _max) external onlyOwner {
        maxDailyRewardPerPlayer = _max;
    }

    function setBaseReward(uint256 _base) external onlyOwner {
        baseRewardPerWin = _base;
    }

    function setHalvingFactor(uint256 _bps) external onlyOwner {
        require(_bps > 0 && _bps <= 10000, "Invalid BPS");
        halvingFactorBps = _bps;
    }

    /// @notice Fund the vault with $BCRDI tokens
    function fundVault(uint256 amount) external onlyOwner {
        bcrdiToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    /// @notice Emergency withdraw (for migration)
    function emergencyWithdraw(uint256 amount) external onlyOwner {
        bcrdiToken.safeTransfer(owner(), amount);
    }
}
