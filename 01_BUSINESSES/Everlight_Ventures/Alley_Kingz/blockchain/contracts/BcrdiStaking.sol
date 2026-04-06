// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title BcrdiStaking
 * @dev Stake $BCRDI, earn yield + qualify for Dog NFT airdrops
 *
 * Staking tiers (by amount staked):
 *   Bronze: 1,000+ BCRDI    -- base yield
 *   Silver: 10,000+ BCRDI   -- 1.5x yield + monthly Dog airdrop eligibility
 *   Gold:   50,000+ BCRDI   -- 2x yield + monthly Dog airdrop + exclusive Car NFTs
 *   Diamond: 100,000+ BCRDI -- 3x yield + all perks + governance voting weight
 */
contract BcrdiStaking is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public bcrdiToken;

    // Staking tiers
    uint256 public constant BRONZE_MIN = 1_000 * 1e18;
    uint256 public constant SILVER_MIN = 10_000 * 1e18;
    uint256 public constant GOLD_MIN = 50_000 * 1e18;
    uint256 public constant DIAMOND_MIN = 100_000 * 1e18;

    // Reward rate: tokens per second per staked token (scaled by 1e18)
    uint256 public rewardRate;
    uint256 public lastUpdateTime;
    uint256 public rewardPerTokenStored;

    // Totals
    uint256 public totalStaked;
    uint256 public totalRewardsPaid;

    // Per-staker data
    struct StakeInfo {
        uint256 amount;
        uint256 rewardPerTokenPaid;
        uint256 rewardsEarned;
        uint256 stakedAt;
        uint256 lastClaimTime;
    }

    mapping(address => StakeInfo) public stakes;

    // Airdrop eligibility snapshot
    address[] public stakerList;
    mapping(address => bool) private isStaker;

    // Lock period (optional, 0 = no lock)
    uint256 public lockPeriod;

    event Staked(address indexed user, uint256 amount, uint8 tier);
    event Unstaked(address indexed user, uint256 amount);
    event RewardClaimed(address indexed user, uint256 amount);
    event RewardRateUpdated(uint256 newRate);

    constructor(address _bcrdiToken) Ownable(msg.sender) {
        bcrdiToken = IERC20(_bcrdiToken);
        rewardRate = 0; // Set after reward pool is funded
    }

    // --- Modifiers ---

    modifier updateReward(address account) {
        rewardPerTokenStored = rewardPerToken();
        lastUpdateTime = block.timestamp;
        if (account != address(0)) {
            stakes[account].rewardsEarned = earned(account);
            stakes[account].rewardPerTokenPaid = rewardPerTokenStored;
        }
        _;
    }

    // --- Core Functions ---

    /// @notice Stake $BCRDI tokens
    function stake(uint256 amount) external nonReentrant updateReward(msg.sender) {
        require(amount > 0, "Cannot stake 0");

        bcrdiToken.safeTransferFrom(msg.sender, address(this), amount);

        stakes[msg.sender].amount += amount;
        stakes[msg.sender].stakedAt = block.timestamp;
        totalStaked += amount;

        if (!isStaker[msg.sender]) {
            stakerList.push(msg.sender);
            isStaker[msg.sender] = true;
        }

        emit Staked(msg.sender, amount, getTier(msg.sender));
    }

    /// @notice Unstake $BCRDI tokens
    function unstake(uint256 amount) external nonReentrant updateReward(msg.sender) {
        require(amount > 0, "Cannot unstake 0");
        require(stakes[msg.sender].amount >= amount, "Insufficient stake");
        if (lockPeriod > 0) {
            require(
                block.timestamp >= stakes[msg.sender].stakedAt + lockPeriod,
                "Lock period active"
            );
        }

        stakes[msg.sender].amount -= amount;
        totalStaked -= amount;

        bcrdiToken.safeTransfer(msg.sender, amount);
        emit Unstaked(msg.sender, amount);
    }

    /// @notice Claim earned rewards
    function claimRewards() external nonReentrant updateReward(msg.sender) {
        uint256 reward = stakes[msg.sender].rewardsEarned;
        require(reward > 0, "No rewards");

        stakes[msg.sender].rewardsEarned = 0;
        stakes[msg.sender].lastClaimTime = block.timestamp;
        totalRewardsPaid += reward;

        bcrdiToken.safeTransfer(msg.sender, reward);
        emit RewardClaimed(msg.sender, reward);
    }

    /// @notice Stake + claim in one transaction
    function compound() external nonReentrant updateReward(msg.sender) {
        uint256 reward = stakes[msg.sender].rewardsEarned;
        require(reward > 0, "No rewards");

        stakes[msg.sender].rewardsEarned = 0;
        stakes[msg.sender].amount += reward;
        totalStaked += reward;
        totalRewardsPaid += reward;

        emit RewardClaimed(msg.sender, reward);
        emit Staked(msg.sender, reward, getTier(msg.sender));
    }

    // --- View Functions ---

    function rewardPerToken() public view returns (uint256) {
        if (totalStaked == 0) return rewardPerTokenStored;
        return rewardPerTokenStored +
            ((block.timestamp - lastUpdateTime) * rewardRate * 1e18) / totalStaked;
    }

    function earned(address account) public view returns (uint256) {
        StakeInfo memory s = stakes[account];
        uint256 tierMultiplier = _getTierMultiplier(s.amount);
        return
            ((s.amount * (rewardPerToken() - s.rewardPerTokenPaid) * tierMultiplier) / (1e18 * 100)) +
            s.rewardsEarned;
    }

    function getTier(address account) public view returns (uint8) {
        uint256 amount = stakes[account].amount;
        if (amount >= DIAMOND_MIN) return 4;
        if (amount >= GOLD_MIN) return 3;
        if (amount >= SILVER_MIN) return 2;
        if (amount >= BRONZE_MIN) return 1;
        return 0;
    }

    function _getTierMultiplier(uint256 amount) internal pure returns (uint256) {
        if (amount >= DIAMOND_MIN) return 300; // 3x
        if (amount >= GOLD_MIN) return 200;    // 2x
        if (amount >= SILVER_MIN) return 150;  // 1.5x
        return 100;                            // 1x
    }

    /// @notice Get all stakers eligible for airdrop (Silver+ tier)
    function getAirdropEligible() external view returns (address[] memory) {
        uint256 count;
        for (uint256 i = 0; i < stakerList.length; i++) {
            if (stakes[stakerList[i]].amount >= SILVER_MIN) {
                count++;
            }
        }

        address[] memory eligible = new address[](count);
        uint256 idx;
        for (uint256 i = 0; i < stakerList.length; i++) {
            if (stakes[stakerList[i]].amount >= SILVER_MIN) {
                eligible[idx++] = stakerList[i];
            }
        }
        return eligible;
    }

    function stakerCount() external view returns (uint256) {
        return stakerList.length;
    }

    // --- Admin ---

    /// @notice Set reward rate (tokens per second per total staked, scaled by 1e18)
    function setRewardRate(uint256 _rate) external onlyOwner updateReward(address(0)) {
        rewardRate = _rate;
        emit RewardRateUpdated(_rate);
    }

    /// @notice Set lock period (0 = no lock)
    function setLockPeriod(uint256 _period) external onlyOwner {
        lockPeriod = _period;
    }

    /// @notice Fund the staking contract with reward tokens
    function fundRewards(uint256 amount) external onlyOwner {
        bcrdiToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    /// @notice Emergency withdraw (owner only, for migration)
    function emergencyWithdraw(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner(), amount);
    }
}
