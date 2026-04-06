

using System;

namespace ArenaAdvance.Data
{
    public enum CardRarity
    {
        Common,
        Rare,
        Epic,
        Legendary
    }

    public enum CardType
    {
        Troop,
        Spell,
        Building
    }

    public enum TargetType
    {
        Ground,
        Air,
        Both,
        Buildings
    }

    public enum Arena
    {
        TrainingCamp = 0,
        GoblinStadium = 1,
        BonePit = 2,
        BarbarianBowl = 3,
        SpellValley = 4,
        BuildersWorkshop = 5,
        RoyalArena = 6,
        FrozenPeak = 7,
        JungleArena = 8,
        HogMountain = 9,
        ElectroValley = 10
    }

    public enum League
    {
        None,
        Bronze,
        Silver,
        Gold,
        Platinum,
        Diamond,
        Champion,
        GrandChampion
    }

    public enum MatchResult
    {
        Win,
        Loss,
        Draw
    }

    public enum ContractType
    {
        Pass,           // Season Pass advance
        Upgrade,        // Card upgrade bundle
        Cosmetic,       // Skins, emotes, etc.
        Access          // Special mode access
    }

    public enum ContractStatus
    {
        Available,
        Active,
        Succeeded,
        Failed,
        Settled
    }

    public enum CreditTier
    {
        Bronze,     // 0-20 score
        Silver,     // 21-50 score
        Gold,       // 51-80 score
        Platinum    // 81-100+ score
    }

    public enum SettlementOption
    {
        PayGems,
        ForfeitRewards,
        RedemptionQuest
    }

    public enum ChestType
    {
        Silver,
        Gold,
        Giant,
        Magical,
        SuperMagical,
        Epic,
        Legendary
    }

    public enum GameState
    {
        MainMenu,
        Matchmaking,
        Battle,
        PostMatch,
        Shop,
        Collection,
        Contracts
    }
}
