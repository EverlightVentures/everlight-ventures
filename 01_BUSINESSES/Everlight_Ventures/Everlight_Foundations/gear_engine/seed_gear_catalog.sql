-- Seed initial gear catalog for Daily Drop Engine
-- Run this in Supabase SQL Editor once to bootstrap the catalog
-- These are high-rated HIM gear items with affiliate links

insert into gear_catalog (title, description, image_url, url, seller, rating, sales_velocity, commission_pct, stock, category)
values
  (
    'TRX HOME2 Suspension Trainer System',
    'The gold standard for bodyweight training. 300+ exercises, anchor anywhere, compact and travel-ready. Trusted by military and elite athletes.',
    'https://m.media-amazon.com/images/I/71o0VBB7VRL._AC_SL1500_.jpg',
    'https://www.amazon.com/dp/B00H5N7QOK?tag=everlightv-20',
    'TRX Training', 4.7, 420, 4.5, 100, 'fitness'
  ),
  (
    'Garmin Forerunner 255 GPS Running Watch',
    'Advanced running dynamics, HRV status tracking, race predictor, and up to 14-day battery. The serious runner''s watch.',
    'https://m.media-amazon.com/images/I/71l3vy5cPeL._AC_SL1500_.jpg',
    'https://www.amazon.com/dp/B0B3DRDLJF?tag=everlightv-20',
    'Garmin', 4.8, 380, 5.0, 100, 'wearables'
  ),
  (
    'WHOOP 4.0 Performance Tracker',
    '24/7 strain, recovery, and sleep coaching. No screen, no distractions -- just data. Used by NFL, NBA, and Olympic athletes.',
    'https://m.media-amazon.com/images/I/61-ydCH2ZkL._AC_SL1500_.jpg',
    'https://www.amazon.com/dp/B09NKP52TM?tag=everlightv-20',
    'WHOOP', 4.5, 520, 6.0, 100, 'wearables'
  ),
  (
    'Hydrow Wave Rowing Machine',
    'Live and on-demand rowing classes on a 16-inch screen. 86 lb compact build. Rated #1 connected rowing machine 2025.',
    'https://m.media-amazon.com/images/I/71AZfqS9oNL._AC_SL1500_.jpg',
    'https://www.amazon.com/dp/B09XY4K5QQ?tag=everlightv-20',
    'Hydrow', 4.6, 150, 8.0, 25, 'cardio'
  ),
  (
    'Theragun Pro Plus Percussive Massage Device',
    'Professional-grade recovery. 6 attachments, heated head, cooling vibration, 300-minute battery. The recovery tool of champions.',
    'https://m.media-amazon.com/images/I/61VLUDgXJhL._AC_SL1500_.jpg',
    'https://www.amazon.com/dp/B0C5QVMNTM?tag=everlightv-20',
    'Therabody', 4.7, 310, 5.5, 100, 'recovery'
  ),
  (
    'Lululemon Surge Jogger 29"',
    'Four-way stretch, sweat-wicking, anti-stink tech. The best-rated performance jogger for training and daily wear.',
    'https://images.lululemon.com/is/image/lululemon/LM5BM2S_0001_1',
    'https://www.amazon.com/s?k=lululemon+surge+jogger&tag=everlightv-20',
    'Lululemon', 4.6, 280, 3.5, 100, 'apparel'
  ),
  (
    'Momentous Essential Grass-Fed Whey Protein',
    'NSF Certified for Sport. Clean label whey, 25g protein, no artificial junk. Trusted by pro athletes and serious lifters.',
    'https://m.media-amazon.com/images/I/71f3pzYDXnL._AC_SL1500_.jpg',
    'https://www.amazon.com/dp/B08Y6DLPB5?tag=everlightv-20',
    'Momentous', 4.7, 450, 7.0, 100, 'nutrition'
  ),
  (
    'Bowflex SelectTech 552 Adjustable Dumbbells',
    'Replaces 15 sets of weights. 5-52.5 lb range, dial-a-weight in seconds. The #1 rated adjustable dumbbell on Amazon.',
    'https://m.media-amazon.com/images/I/71EkBBpCYnL._AC_SL1500_.jpg',
    'https://www.amazon.com/dp/B001ARYU58?tag=everlightv-20',
    'Bowflex', 4.8, 600, 5.0, 50, 'strength'
  )
on conflict do nothing;
