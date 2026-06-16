# 用法:
#   1. 清空所有表（含 superuser）+ Redis:
#        docker exec -it chirp_web python manage.py flush
#        docker exec -it chirp_redis redis-cli flushall
#
#   2. 如需保留 admin 账号，重新创建 superuser:
#        docker exec -it chirp_web python manage.py createsuperuser
#
#   3. 运行 seed 脚本:
#        docker exec -it chirp_web python manage.py seed_data
#
# 效果:
#   1. 创建 10 个动物主题用户（密码统一 test1234），从 picsum.photos 下载头像
#   2. 建立 35 条关注关系（含互相关注与单向关注）
#   3. 创建 100 条推文（每个用户 10 条），每条按 TWEETS 中指定的数量附 0~4 张风景图（picsum.photos）
#   4. 每条推文自动触发 Celery fanout 到关注者的 newsfeed
#   5. LANDSCAPE_SEEDS 中的图片全部下载并保存到 media，推文复用这些已保存的图片

import requests
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from friendships.services import FriendshipService
from newsfeeds.services import NewsFeedService
from tweets.constants import TweetPhotoStatus
from tweets.models import Tweet, TweetPhoto

USERS = [
    {'username': 'dog_husky',   'nickname': 'Husky',      'email': 'dog_husky@chirp.com'},
    {'username': 'dog_corgi',   'nickname': 'Corgi',      'email': 'dog_corgi@chirp.com'},
    {'username': 'dog_shiba',   'nickname': 'Shiba',      'email': 'dog_shiba@chirp.com'},
    {'username': 'dog_golden',  'nickname': 'Golden',     'email': 'dog_golden@chirp.com'},
    {'username': 'dog_poodle',  'nickname': 'Poodle',     'email': 'dog_poodle@chirp.com'},
    {'username': 'cat_persian', 'nickname': 'Persian',    'email': 'cat_persian@chirp.com'},
    {'username': 'cat_siamese', 'nickname': 'Siamese',    'email': 'cat_siamese@chirp.com'},
    {'username': 'cat_ragdoll', 'nickname': 'Ragdoll',    'email': 'cat_ragdoll@chirp.com'},
    {'username': 'cat_bengal',  'nickname': 'Bengal',     'email': 'cat_bengal@chirp.com'},
    {'username': 'cat_maine',   'nickname': 'Maine Coon', 'email': 'cat_maine@chirp.com'},
]

# from → to（A 关注了谁）, 共 35 条
# 既有互相关注（如 dog_husky ↔ dog_corgi），也有单向关注（如 dog_corgi → cat_maine）
FOLLOWS = {
    'dog_husky':   ['dog_corgi', 'dog_shiba', 'cat_persian', 'cat_siamese'],
    'dog_corgi':   ['dog_husky', 'dog_golden', 'cat_ragdoll', 'cat_maine'],
    'dog_shiba':   ['dog_husky', 'dog_poodle', 'cat_bengal'],
    'dog_golden':  ['dog_corgi', 'dog_poodle', 'cat_persian', 'cat_maine'],
    'dog_poodle':  ['dog_shiba', 'dog_golden', 'cat_siamese', 'cat_bengal'],
    'cat_persian': ['dog_husky', 'cat_ragdoll', 'cat_bengal'],
    'cat_siamese': ['dog_husky', 'cat_persian', 'cat_maine'],
    'cat_ragdoll': ['dog_corgi', 'cat_siamese', 'cat_bengal'],
    'cat_bengal':  ['dog_shiba', 'cat_persian', 'cat_ragdoll'],
    'cat_maine':   ['dog_golden', 'cat_siamese', 'cat_bengal', 'cat_ragdoll'],
}

# 反向视角（由上面的 FOLLOWS 推导）: to → from（谁关注了 A，即 A 的粉丝）, 共 35 条
# FOLLOWERS = {
#     'dog_husky':   ['dog_corgi', 'dog_shiba', 'cat_persian', 'cat_siamese'],
#     'dog_corgi':   ['dog_husky', 'dog_golden', 'cat_ragdoll'],
#     'dog_shiba':   ['dog_husky', 'dog_poodle', 'cat_bengal'],
#     'dog_golden':  ['dog_corgi', 'dog_poodle', 'cat_maine'],
#     'dog_poodle':  ['dog_shiba', 'dog_golden'],
#     'cat_persian': ['dog_husky', 'dog_golden', 'cat_siamese', 'cat_bengal'],
#     'cat_siamese': ['dog_husky', 'dog_poodle', 'cat_ragdoll', 'cat_maine'],
#     'cat_ragdoll': ['dog_corgi', 'cat_persian', 'cat_bengal', 'cat_maine'],
#     'cat_bengal':  ['dog_shiba', 'dog_poodle', 'cat_persian', 'cat_ragdoll', 'cat_maine'],
#     'cat_maine':   ['dog_corgi', 'dog_golden', 'cat_siamese'],
# }

# (username, content, num_photos) —— num_photos 固定写死, 取值 0~4
TWEETS = [
    ('dog_husky',   'Just went on the best trail run today. Who else loves morning runs?', 2),
    ('dog_husky',   'Nothing beats a warm fireplace on a cold night.', 0),
    ('dog_husky',   'Snow season is here and I could not be happier.', 3),
    ('dog_husky',   "Found a frozen lake on today's hike. Absolutely stunning.", 4),
    ('dog_husky',   'Cold wind, clear skies, perfect day to be outside.', 1),
    ('dog_husky',   'Packed my bag for a weekend in the wild.', 1),
    ('dog_husky',   'The northern lights are on my bucket list.', 2),
    ('dog_husky',   'Fresh powder and an empty trail. Bliss.', 3),
    ('dog_husky',   'Coffee tastes better outdoors, change my mind.', 0),
    ('dog_husky',   'Crossed a wooden bridge over a roaring creek today.', 4),

    ('dog_corgi',   'Discovered the most amazing coffee shop downtown. #HiddenGem', 0),
    ('dog_corgi',   'Weekend hiking plan: find the tallest hill. Wish me luck!', 2),
    ('dog_corgi',   'Short legs, big adventures. Conquered a new trail today.', 3),
    ('dog_corgi',   'Sunbathing in the meadow is my cardio.', 1),
    ('dog_corgi',   'Rolling hills as far as the eye can see.', 2),
    ('dog_corgi',   'Naps in the sun should count as a hobby.', 0),
    ('dog_corgi',   'Took the long way home through the meadow.', 2),
    ('dog_corgi',   'Tiny paws, endless curiosity.', 1),
    ('dog_corgi',   'Sunrise over the valley never gets old.', 3),
    ('dog_corgi',   'Found a field of wildflowers and lost track of time.', 4),

    ('dog_shiba',   'Learned a new recipe today. Spoiler: it actually worked.', 0),
    ('dog_shiba',   "Sunset views are nature's way of saying good job today.", 3),
    ('dog_shiba',   'Climbed to the top and the view was worth every step.', 4),
    ('dog_shiba',   'Quiet mornings by the river are the best therapy.', 2),
    ('dog_shiba',   'A little fog never hurt a good adventure.', 1),
    ('dog_shiba',   'Tea, a good book, and rain on the window.', 0),
    ('dog_shiba',   'Wandered into a bamboo grove today. Magical.', 2),
    ('dog_shiba',   'The trail rewarded me with a hidden waterfall.', 4),
    ('dog_shiba',   'Stillness by the pond at dawn.', 1),
    ('dog_shiba',   'Mountains in the distance, peace in my heart.', 3),

    ('dog_golden',  'Starting the day with a swim. Join me!', 2),
    ('dog_golden',  'Sometimes the best therapy is a long walk and good music.', 0),
    ('dog_golden',  'The lake was perfectly still this morning.', 3),
    ('dog_golden',  'Chasing waterfalls, literally.', 4),
    ('dog_golden',  'Golden hour really is the best hour.', 1),
    ('dog_golden',  'Beach day! Sand between the toes is underrated.', 3),
    ('dog_golden',  'Nothing like a lake swim at sunrise.', 2),
    ('dog_golden',  'Rolling in the grass is self-care.', 0),
    ('dog_golden',  'Followed the river until it met the sea.', 4),
    ('dog_golden',  'Sunset paddle on calm water.', 1),

    ('dog_poodle',  'Spent the afternoon reading in the park. Highly recommend.', 1),
    ('dog_poodle',  'Hot take: rainy days are underrated. Perfect excuse to stay in.', 0),
    ('dog_poodle',  'Wandered through a pine forest today. So peaceful.', 3),
    ('dog_poodle',  'The mountains are calling and I must go.', 2),
    ('dog_poodle',  'Fresh air and good views, what more do you need?', 2),
    ('dog_poodle',  'Curated a tiny reading nook by the window.', 0),
    ('dog_poodle',  'Strolled through an autumn forest today.', 3),
    ('dog_poodle',  'The fog made the whole valley feel like a dream.', 2),
    ('dog_poodle',  'A quiet trail and good company.', 1),
    ('dog_poodle',  'Reached the ridge just in time for golden hour.', 4),

    ('cat_persian', 'Found a sunny spot by the window. Not moving for the rest of the day.', 0),
    ('cat_persian', 'Tried meditating this morning. Very peaceful. 10/10 recommend.', 1),
    ('cat_persian', 'Watching the waves roll in from the cliffs.', 4),
    ('cat_persian', 'Desert sunsets hit different.', 3),
    ('cat_persian', 'Calm seas and a clear horizon.', 2),
    ('cat_persian', 'Window seat, warm sun, zero responsibilities.', 0),
    ('cat_persian', 'Watched the tide come in all afternoon.', 2),
    ('cat_persian', 'Dunes for days out in the desert.', 3),
    ('cat_persian', 'A gentle breeze off the bay.', 1),
    ('cat_persian', 'Cliffside views that take your breath away.', 4),

    ('cat_siamese', 'The city skyline at night is something else entirely.', 0),
    ('cat_siamese', "Just adopted a little plant family. Hoping I don't kill them.", 1),
    ('cat_siamese', 'Took the scenic route along the coast today.', 3),
    ('cat_siamese', 'Misty mountains in the early morning light.', 2),
    ('cat_siamese', 'Blue skies and endless fields.', 2),
    ('cat_siamese', 'City lights or starry skies? Why not both.', 0),
    ('cat_siamese', 'My plant family is officially thriving.', 1),
    ('cat_siamese', 'Drove the coast road with the windows down.', 3),
    ('cat_siamese', 'Layers of mountains fading into the haze.', 2),
    ('cat_siamese', 'Endless fields under a bright blue sky.', 4),

    ('cat_ragdoll', "Lazy Sunday mornings are truly one of life's greatest gifts.", 0),
    ('cat_ragdoll', 'Ocean breeze and no plans. This is living.', 3),
    ('cat_ragdoll', 'Curled up watching the rain over the valley.', 1),
    ('cat_ragdoll', 'The canyon at dusk is pure magic.', 4),
    ('cat_ragdoll', 'Rivers always know the way.', 2),
    ('cat_ragdoll', 'Sundays were made for slow mornings.', 0),
    ('cat_ragdoll', 'Listened to the waves until I lost track of time.', 3),
    ('cat_ragdoll', 'Rain over the valley is my favorite soundtrack.', 1),
    ('cat_ragdoll', 'Hiked into the canyon at first light.', 4),
    ('cat_ragdoll', 'Followed the river bend after bend.', 2),

    ('cat_bengal',  'Explored a new neighborhood today. Hidden gems everywhere.', 1),
    ('cat_bengal',  'Cooking > takeout. Fight me.', 0),
    ('cat_bengal',  'Prowling through the tall grass at golden hour.', 3),
    ('cat_bengal',  'Found the wildest view at the edge of the cliff.', 4),
    ('cat_bengal',  'Snowy peaks and a thermos of tea. Perfect.', 2),
    ('cat_bengal',  'Discovered a rooftop with the best view in town.', 1),
    ('cat_bengal',  'Homemade dinner > anything delivered. Period.', 0),
    ('cat_bengal',  'Stalked through the savanna grass at sunset.', 3),
    ('cat_bengal',  'Stood at the cliff edge and felt tiny.', 4),
    ('cat_bengal',  'Snow on the peaks, fire in the cabin.', 2),

    ('cat_maine',   'Early morning fog over the mountains is absolutely magical.', 3),
    ('cat_maine',   'Finished a 1000-piece puzzle. I deserve a medal.', 0),
    ('cat_maine',   'Big cat, bigger mountains.', 4),
    ('cat_maine',   'The forest is quietest right after the rain.', 2),
    ('cat_maine',   'Stargazing from the lakeshore tonight.', 1),
    ('cat_maine',   'Morning mist makes the mountains look unreal.', 3),
    ('cat_maine',   'Built a fort out of books today. No regrets.', 0),
    ('cat_maine',   'Big paws, bigger summit dreams.', 4),
    ('cat_maine',   'The woods smell incredible after the rain.', 2),
    ('cat_maine',   'Counted the stars from the lakeside last night.', 1),
]

# picsum 固定 seed，每次下载同一张图（全部为风景图）
LANDSCAPE_SEEDS = [
    'forest1', 'mountain1', 'ocean1', 'sunset1', 'lake1',
    'forest2', 'mountain2', 'ocean2', 'sunset2', 'lake2',
    'forest3', 'mountain3', 'ocean3', 'sunset3', 'lake3',
    'forest4', 'mountain4', 'ocean4', 'sunset4', 'lake4',
    'forest5', 'mountain5', 'ocean5', 'sunset5', 'lake5',
    'desert1', 'field1', 'snow1', 'river1', 'canyon1',
    'desert2', 'field2', 'snow2', 'river2', 'canyon2',
    'desert3', 'field3', 'snow3', 'river3', 'canyon3',
    'desert4', 'field4', 'snow4', 'river4', 'canyon4',
    'desert5', 'field5', 'snow5', 'river5', 'canyon5',
]


class Command(BaseCommand):
    help = 'Seed database: 10 animal users + 35 friendships + 100 tweets with photos'

    def handle(self, *args, **options):
        self.stdout.write('Creating users...')
        user_map = self._create_users()

        self.stdout.write('Creating friendships...')
        self._create_friendships(user_map)

        self.stdout.write('Downloading landscapes...')
        landscape_files = self._download_landscapes()

        self.stdout.write('Creating tweets...')
        self._create_tweets(user_map, landscape_files)

        self.stdout.write(self.style.SUCCESS('Seed complete!'))

    def _download(self, url, filename):
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return ContentFile(res.content, name=filename)
        except Exception as e:
            self.stdout.write(f'  Warning: failed to download {url}: {e}')
        return None

    def _create_users(self):
        user_map = {}
        for data in USERS:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password='test1234',
            )
            profile = user.profile
            profile.nickname = data['nickname']

            avatar_name = f"{data['username']}.jpg"
            if default_storage.exists(avatar_name):
                # 头像已存在则跳过下载，直接复用 media 里的图片
                profile.avatar.name = avatar_name
                self.stdout.write(f'  avatar {avatar_name} already exists, skip')
            else:
                img = self._download(
                    url=f"https://picsum.photos/seed/{data['username']}/300/300",
                    filename=avatar_name,
                )
                if img:
                    profile.avatar.save(avatar_name, img, save=False)

            profile.save()
            user_map[data['username']] = user
            self.stdout.write(f"  {data['username']} ({data['nickname']})")
        return user_map

    def _create_friendships(self, user_map):
        count = 0
        for from_username, to_usernames in FOLLOWS.items():
            for to_username in to_usernames:
                FriendshipService.follow(
                    from_user_id=user_map[from_username].id,
                    to_user_id=user_map[to_username].id,
                )
                count += 1
        self.stdout.write(f'  {count} follow relationships created')

    def _download_landscapes(self):
        # 把 LANDSCAPE_SEEDS 里的图片全部下载并保存到 media，返回 {seed: 存储文件名}
        # 推文阶段复用这些文件名，避免重复下载，也保证图片都已落地到 media
        landscape_files = {}
        for seed in LANDSCAPE_SEEDS:
            filename = f"{seed}.jpg"
            # 已存在则跳过下载，直接复用 media 里的图片，检查下一个
            if default_storage.exists(filename):
                landscape_files[seed] = filename
                self.stdout.write(f'  landscape {seed} already exists, skip')
                continue
            img = self._download(
                url=f"https://picsum.photos/seed/{seed}/600/400",
                filename=filename,
            )
            if img:
                name = default_storage.save(filename, img)
                landscape_files[seed] = name
                self.stdout.write(f'  landscape {seed} -> {name}')
            else:
                self.stdout.write(f'  Warning: landscape {seed} skipped')
        self.stdout.write(f'  {len(landscape_files)} landscapes available in media')
        return landscape_files

    def _create_tweets(self, user_map, landscape_files):
        seed_idx = 0
        total_seeds = len(LANDSCAPE_SEEDS)

        for username, content, num_photos in TWEETS:
            user = user_map[username]
            tweet = Tweet.objects.create(user=user, content=content)

            photos = []
            for order in range(num_photos):
                # 从 LANDSCAPE_SEEDS 循环取下一张已成功下载的图片
                seed = None
                for _ in range(total_seeds):
                    candidate = LANDSCAPE_SEEDS[seed_idx % total_seeds]
                    seed_idx += 1
                    if candidate in landscape_files:
                        seed = candidate
                        break
                if seed is None:
                    break

                photo = TweetPhoto(
                    tweet=tweet,
                    user=user,
                    order=order,
                    status=TweetPhotoStatus.APPROVED,
                )
                # 复用已保存到 media 的图片文件，不再重复写文件
                photo.file.name = landscape_files[seed]
                photos.append(photo)

            if photos:
                TweetPhoto.objects.bulk_create(photos)

            NewsFeedService.fanout_to_followers(tweet=tweet)
            self.stdout.write(f'  [{username}] {num_photos} photos | {content[:40]}...')
