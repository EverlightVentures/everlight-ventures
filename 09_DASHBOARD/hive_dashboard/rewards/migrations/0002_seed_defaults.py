"""
Seed default CompThresholds and DailyLoginRewards.
These are the starting config -- all adjustable in Django admin.
"""
from django.db import migrations


def seed_comp_thresholds(apps, schema_editor):
    CompThreshold = apps.get_model("rewards", "CompThreshold")

    thresholds = [
        # (name, spend_dollars, comp_type, value, repeating)
        ("First $25 Comp",       25,    "chips_bonus",     "500 bonus chips",          False),
        ("$50 Milestone",        50,    "chips_bonus",     "1,000 bonus chips",        False),
        ("$100 Spender",         100,   "vip_trial",       "7-day VIP trial",          False),
        ("$250 High Roller",     250,   "service_voucher", "$10 Everlight credit",     False),
        ("$500 VIP",             500,   "merch",           "Everlight branded merch",  False),
        ("$1000 Legend",         1000,  "free_month",      "1 free month subscription",False),
        ("Recurring $50 Chips",  50,    "chips_bonus",     "500 bonus chips",          True),
    ]

    for name, dollars, comp_type, value, repeating in thresholds:
        CompThreshold.objects.get_or_create(
            name=name,
            defaults={
                "spend_threshold_cents": dollars * 100,
                "comp_type": comp_type,
                "comp_value": value,
                "points_cost": 0,
                "is_active": True,
                "is_repeating": repeating,
            }
        )


def seed_daily_login_rewards(apps, schema_editor):
    DailyLoginReward = apps.get_model("rewards", "DailyLoginReward")

    rewards = [
        # (day, points, is_milestone, chips, gems, label)
        (1,   15,  False, 0,    0,   "Day 1"),
        (2,   15,  False, 0,    0,   "Day 2"),
        (3,   20,  False, 100,  0,   "Day 3"),
        (4,   15,  False, 0,    0,   "Day 4"),
        (5,   20,  False, 0,    0,   "Day 5"),
        (6,   25,  False, 200,  0,   "Day 6"),
        (7,   50,  True,  500,  5,   "Week 1 Complete!"),
        (14,  60,  True,  750,  10,  "2-Week Streak!"),
        (21,  70,  True,  1000, 15,  "3-Week Streak!"),
        (30,  150, True,  2000, 25,  "Month Streak - LEGEND"),
        (60,  200, True,  3000, 50,  "2-Month Streak - INSANE"),
        (100, 300, True,  5000, 100, "100-Day Streak - GOD MODE"),
        (365, 750, True,  10000,250, "365-Day Streak - Hall of Fame"),
    ]

    for day, pts, milestone, chips, gems, label in rewards:
        DailyLoginReward.objects.get_or_create(
            streak_day=day,
            defaults={
                "points_reward": pts,
                "is_milestone": milestone,
                "chips_bonus": chips,
                "gems_bonus": gems,
                "label": label,
            }
        )


def reverse_seeds(apps, schema_editor):
    # Non-destructive -- leave data in place on rollback
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("rewards", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_comp_thresholds, reverse_seeds),
        migrations.RunPython(seed_daily_login_rewards, reverse_seeds),
    ]
