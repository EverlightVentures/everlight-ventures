"""
python manage.py seed_blackjack

Seeds cosmetic items, gem packages, and default avatar options.
Safe to run multiple times (uses get_or_create).
"""
from django.core.management.base import BaseCommand
from blackjack.models import CosmeticItem, GemPackage


COSMETICS = [
    # Outfits
    dict(item_id='gold_tux',       name='Gold Tuxedo',       category='outfit',     rarity='rare',
         description='Sharp gold tuxedo. Boosts table presence.',
         price_chips=5000, price_gems=0, rank_required='Silver',
         visual_config={'color': '#c9a84c', 'score': 1.15}),
    dict(item_id='diamond_blazer', name='Diamond Blazer',    category='outfit',     rarity='epic',
         description='Studded with synthetic diamonds. Serious clout.',
         price_chips=15000, price_gems=0, rank_required='Gold',
         visual_config={'color': '#b9f2ff', 'score': 1.25}),
    dict(item_id='neon_suit',      name='Neon Synthwave Suit', category='outfit',   rarity='rare',
         description='80s-inspired neon. Lights up the table.',
         price_chips=0, price_gems=50, rank_required='Bronze',
         visual_config={'color': '#ff00ff', 'score': 1.20}),
    dict(item_id='royal_robe',     name='Royal Robe',         category='outfit',    rarity='epic',
         description='For Platinum-tier players only.',
         price_chips=0, price_gems=120, rank_required='Platinum',
         visual_config={'color': '#6c3483', 'score': 1.35}),
    dict(item_id='legendary_drip', name='Legend Drip',        category='outfit',    rarity='legendary',
         description='Exclusive to Legends. Maximum presence.',
         price_chips=0, price_gems=300, rank_required='Legend',
         visual_config={'color': '#ff6b35', 'score': 1.50}),

    # Auras
    dict(item_id='golden_glow',    name='Golden Glow Aura',   category='aura',      rarity='common',
         description='Subtle gold shimmer around your avatar.',
         price_chips=2000, price_gems=0, rank_required='Bronze',
         visual_config={'shader': 'golden', 'score': 1.05}),
    dict(item_id='hologram_blue',  name='Hologram Aura',      category='aura',      rarity='rare',
         description='Sci-fi blue hologram projection.',
         price_chips=0, price_gems=40, rank_required='Silver',
         visual_config={'shader': 'hologram', 'score': 1.10}),
    dict(item_id='fire_aura',      name='Fire Aura',          category='aura',      rarity='epic',
         description='Blazing fire effect. Hot hands only.',
         price_chips=0, price_gems=80, rank_required='Gold',
         visual_config={'shader': 'fire', 'score': 1.15}),
    dict(item_id='legend_aura',    name='Legend Aura',        category='aura',      rarity='legendary',
         description='Legendary players only. Intimidate the dealer.',
         price_chips=0, price_gems=200, rank_required='Legend',
         visual_config={'shader': 'legend', 'score': 1.25}),

    # Card Backs
    dict(item_id='card_dragon',    name='Dragon Card Back',   category='card_back', rarity='rare',
         description='Embossed dragon pattern.',
         price_chips=3000, price_gems=0, rank_required='Bronze',
         visual_config={'design': 'dragon'}),
    dict(item_id='card_gold',      name='Gold Foil Card Back', category='card_back', rarity='epic',
         description='Shimmering gold foil finish.',
         price_chips=0, price_gems=60, rank_required='Gold',
         visual_config={'design': 'gold_foil'}),
    dict(item_id='card_space',     name='Deep Space Card Back', category='card_back', rarity='epic',
         description='Nebula and stars on every card.',
         price_chips=0, price_gems=75, rank_required='Silver',
         visual_config={'design': 'space'}),

    # Table Felts
    dict(item_id='felt_crimson',   name='Crimson Felt',       category='table_felt', rarity='rare',
         description='Deep red casino felt.',
         price_chips=4000, price_gems=0, rank_required='Silver',
         visual_config={'color': '#8b0000'}),
    dict(item_id='felt_midnight',  name='Midnight Blue Felt', category='table_felt', rarity='epic',
         description='Midnight blue with gold trim.',
         price_chips=0, price_gems=90, rank_required='Gold',
         visual_config={'color': '#00008b'}),
    dict(item_id='felt_legend',    name='Legend Black Felt',  category='table_felt', rarity='legendary',
         description='Matte black with holographic trim. Legend-exclusive.',
         price_chips=0, price_gems=250, rank_required='Legend',
         visual_config={'color': '#111', 'trim': 'holographic'}),

    # Titles
    dict(item_id='title_high_roller', name='High Roller',     category='title',     rarity='rare',
         description='Win 10,000+ chips in a single session.',
         price_chips=0, price_gems=0, rank_required='Gold',
         visual_config={'unlock': 'achievement'}),
    dict(item_id='title_the_shark', name='The Shark',         category='title',     rarity='epic',
         description='Maintain 60%+ win rate over 100 hands.',
         price_chips=0, price_gems=0, rank_required='Platinum',
         visual_config={'unlock': 'achievement'}),
    dict(item_id='title_casino_king', name='Casino King',     category='title',     rarity='legendary',
         description='Reach Legend rank.',
         price_chips=0, price_gems=0, rank_required='Legend',
         visual_config={'unlock': 'rank'}),

    # Accessories
    dict(item_id='acc_sunglasses', name='Gold Aviators',      category='accessory', rarity='common',
         description='Classic gold-framed aviator shades.',
         price_chips=1500, price_gems=0, rank_required='Bronze',
         visual_config={'slot': 'glasses', 'color': '#c9a84c'}),
    dict(item_id='acc_cigar',      name='Lucky Cigar',        category='accessory', rarity='rare',
         description='Old-school casino accessory.',
         price_chips=0, price_gems=30, rank_required='Silver',
         visual_config={'slot': 'prop', 'type': 'cigar'}),
    dict(item_id='acc_crown',      name='Platinum Crown',     category='accessory', rarity='epic',
         description='Show them who runs this table.',
         price_chips=0, price_gems=100, rank_required='Platinum',
         visual_config={'slot': 'hat', 'type': 'crown'}),
]

GEM_PACKAGES = [
    dict(name='Starter Pack',  gems=100, bonus_gems=0,  price_usd='0.99', is_featured=False),
    dict(name='Player Pack',   gems=500, bonus_gems=100, price_usd='4.99', is_featured=False),
    dict(name='High Roller',   gems=1200, bonus_gems=400, price_usd='9.99', is_featured=True),
    dict(name='VIP Bundle',    gems=3000, bonus_gems=1000, price_usd='24.99', is_featured=False),
    dict(name='Casino Boss',   gems=7000, bonus_gems=3000, price_usd='49.99', is_featured=False),
]


class Command(BaseCommand):
    help = 'Seed Everlight Blackjack with default shop items and gem packages'

    def handle(self, *args, **options):
        created_items = 0
        for data in COSMETICS:
            visual = data.pop('visual_config', {})
            obj, created = CosmeticItem.objects.get_or_create(
                item_id=data['item_id'],
                defaults={**data, 'visual_config': visual},
            )
            if not created:
                obj.visual_config = visual
                for k, v in data.items():
                    setattr(obj, k, v)
                obj.save()
            else:
                created_items += 1

        self.stdout.write(f'Cosmetics: {created_items} created, {len(COSMETICS)-created_items} updated')

        created_pkgs = 0
        for data in GEM_PACKAGES:
            obj, created = GemPackage.objects.get_or_create(
                name=data['name'],
                defaults=data,
            )
            if created:
                created_pkgs += 1

        self.stdout.write(f'Gem packages: {created_pkgs} created')
        self.stdout.write(self.style.SUCCESS('Blackjack seed complete.'))
