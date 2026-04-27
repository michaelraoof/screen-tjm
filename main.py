"""
Vision-Based Desktop Automation with Dynamic Icon Grounding
============================================================
1. Fetch 10 posts from JSONPlaceholder API (fallback to hardcoded)
2. For each post:
   a. Show desktop → Gemini vision grounds the Notepad icon → double-click
   b. Type post content, save as post_{id}.txt in Desktop/tjm-project
   c. Close Notepad (handle any unexpected pop-ups via vision)
   d. Repeat with a fresh screenshot for the next post
"""

import io
import json
import os
import subprocess
import time
from pathlib import Path

import mss
import pyautogui
import pyperclip
import pygetwindow as gw
from dotenv import load_dotenv
from openrouter import OpenRouter
from PIL import Image

load_dotenv()

client = OpenRouter(api_key=os.environ["OPENROUTER_API_KEY"])
MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

SAVE_DIR = Path.home() / "Desktop" / "tjm-project"
SAVE_DIR.mkdir(parents=True, exist_ok=True)


FALLBACK_POSTS = [
    {"userId": 1,  "id": 1,  "title": "sunt aut facere repellat provident occaecati excepturi optio reprehenderit", "body": "quia et suscipit\nsuscipit recusandae consequuntur expedita et cum\nreprehenderit molestiae ut ut quas totam\nnostrum rerum est autem sunt rem eveniet architecto"},
    {"userId": 1,  "id": 2,  "title": "qui est esse", "body": "est rerum tempore vitae\nsequi sint nihil reprehenderit dolor beatae ea dolores neque\nfugiat blanditiis voluptate porro vel nihil molestiae ut reiciendis\nqui aperiam non debitis possimus qui neque nisi nulla"},
    {"userId": 1,  "id": 3,  "title": "ea molestias quasi exercitationem repellat qui ipsa sit aut", "body": "et iusto sed quo iure\nvoluptatem occaecati omnis eligendi aut ad\nvoluptatem doloribus vel accusantium quis pariatur\nmolestiae porro eius odio et labore et velit aut"},
    {"userId": 1,  "id": 4,  "title": "eum et est occaecati", "body": "ullam et saepe reiciendis voluptatem adipisci\nsit amet autem assumenda provident rerum culpa\nquis hic commodi nesciunt rem tenetur doloremque ipsam iure\nquis sunt voluptatem rerum illo velit"},
    {"userId": 1,  "id": 5,  "title": "nesciunt quas odio", "body": "repudiandae veniam quaerat sunt sed\nalias aut fugiat sit autem sed est\nvoluptatem omnis possimus esse voluptatibus quis\nest aut tenetur dolor neque"},
    {"userId": 1,  "id": 6,  "title": "dolorem eum magni eos aperiam quia", "body": "ut aspernatur corporis harum nihil quis provident sequi\nmollitia nobis aliquid molestiae\nperspiciatis et ea nemo ab reprehenderit accusantium quas\nvoluptate dolores velit et doloremque molestiae"},
    {"userId": 1,  "id": 7,  "title": "magnam facilis autem", "body": "dolore placeat quibusdam ea quo vitae\nmagni quis enim qui quis quo nemo aut saepe\nquidem repellat excepturi ut quia\nsunt ut sequi eos ea sed quas"},
    {"userId": 1,  "id": 8,  "title": "dolorem dolore est ipsam", "body": "dignissimos aperiam dolorem qui eum\nfacilis quibusdam animi sint suscipit qui sint possimus cum\nquaerat magni maiores excepturi\nipsam ut commodi dolor voluptatum modi aut vitae"},
    {"userId": 1,  "id": 9,  "title": "nesciunt iure omnis dolorem tempora et accusantium", "body": "consectetur animi nesciunt iure dolore\nenim quia ad\nveniam autem ut quam aut nobis\net est aut quod aut provident voluptas autem voluptas"},
    {"userId": 1,  "id": 10, "title": "optio molestias id quia eum", "body": "quo et expedita modi cum officia vel magni\ndoloribus qui repudiandae\nvero nisi sit\nquos veniam quod sed accusamus veritatis error"},
    {"userId": 2,  "id": 11, "title": "et ea vero quia laudantium autem", "body": "delectus reiciendis molestiae occaecati non minima eveniet qui voluptatibus\naccusamus in eum beatae sit\nvel qui neque voluptates ut commodi qui incidunt\nut animi commodi"},
    {"userId": 2,  "id": 12, "title": "in quibusdam tempore odit est dolorem", "body": "itaque id aut magnam\npraesentium quia et ea odit et ea voluptas et\nsapiente quia nihil amet occaecati quia id voluptatem\nincidunt ea est distinctio odio"},
    {"userId": 2,  "id": 13, "title": "dolorum ut in voluptas mollitia et saepe quo animi", "body": "aut dicta possimus sint mollitia voluptas commodi quo doloremque\niste corrupti reiciendis voluptatem eius rerum\nsit cumque quod eligendi laborum minima\nperferendis recusandae assumenda consectetur porro architecto ipsum ipsam"},
    {"userId": 2,  "id": 14, "title": "voluptatem eligendi optio", "body": "fuga et accusamus dolorum perferendis illo voluptas\nnon doloremque neque facere\nad qui dolorum molestiae beatae\nsed aut voluptas totam sit illum"},
    {"userId": 2,  "id": 15, "title": "eveniet quod temporibus", "body": "reprehenderit quos placeat\nvelit minima officia dolores impedit repudiandae molestiae nam\nvoluptas recusandae quis delectus\nofficiis harum fugiat vitae"},
    {"userId": 2,  "id": 16, "title": "sint suscipit perspiciatis velit dolorum rerum ipsa laboriosam odio", "body": "suscipit nam nisi quo aperiam aut\nasperiores eos fugit maiores voluptatibus quia\nvoluptatem quis ullam qui in alias quia est\nconsequatur magni mollitia accusamus ea nisi voluptate dicta"},
    {"userId": 2,  "id": 17, "title": "fugit voluptas sed molestias voluptatem provident", "body": "eos voluptas et aut odit natus earum\naspernatur fuga molestiae ullam\ndeserunt ratione qui eos\nqui nihil ratione nemo velit ut aut id quo"},
    {"userId": 2,  "id": 18, "title": "voluptate et itaque vero tempora molestiae", "body": "eveniet quo quis\nlaborum totam consequatur non dolor\nut et est repudiandae\nest voluptatem vel debitis et magnam"},
    {"userId": 2,  "id": 19, "title": "adipisci placeat illum aut reiciendis qui", "body": "illum quis cupiditate provident sit magnam\nea sed aut omnis\nveniam maiores ullam consequatur atque\nadipisci quo iste expedita sit quos voluptas"},
    {"userId": 2,  "id": 20, "title": "doloribus ad provident suscipit at", "body": "qui consequuntur ducimus possimus quisquam amet similique\nsuscipit porro ipsam amet\neos veritatis officiis exercitationem vel fugit aut necessitatibus totam\nomnis rerum consequatur expedita quidem cumque explicabo"},
    {"userId": 3,  "id": 21, "title": "asperiores ea ipsam voluptatibus modi minima quia sint", "body": "repellat aliquid praesentium dolorem quo\nsed totam minus non itaque\nnihil labore molestiae sunt dolor eveniet hic recusandae veniam\ntempora et tenetur expedita sunt"},
    {"userId": 3,  "id": 22, "title": "dolor sint quo a velit explicabo quia nam", "body": "eos qui et ipsum ipsam suscipit aut\nsed omnis non odio\nexpedita earum mollitia molestiae aut atque rem suscipit\nnam impedit esse"},
    {"userId": 3,  "id": 23, "title": "maxime id vitae nihil numquam", "body": "veritatis unde neque eligendi\nquae quod architecto quo neque vitae\nest illo sit tempora doloremque fugit quod\net et vel beatae sequi ullam sed tenetur perspiciatis"},
    {"userId": 3,  "id": 24, "title": "autem hic labore sunt dolores incidunt", "body": "enim et ex nulla\nomnis voluptas quia qui\nvoluptatem consequatur numquam aliquam sunt\ntotam recusandae id dignissimos aut sed asperiores deserunt"},
    {"userId": 3,  "id": 25, "title": "rem alias distinctio quo quis", "body": "ullam consequatur ut\nomnis quis sit vel consequuntur\nipsa eligendi ipsum molestiae et omnis error nostrum\nmolestiae illo tempore quia et distinctio"},
    {"userId": 3,  "id": 26, "title": "est et quae odit qui non", "body": "similique esse doloribus nihil accusamus\nomnis dolorem fuga consequuntur reprehenderit fugit recusandae temporibus\nperspiciatis cum ut laudantium\nomnis aut molestiae vel vero"},
    {"userId": 3,  "id": 27, "title": "quasi id et eos tenetur aut quo autem", "body": "eum sed dolores ipsam sint possimus debitis occaecati\ndebitis qui qui et\nut placeat enim earum aut odit facilis\nconsequatur suscipit necessitatibus rerum sed inventore temporibus consequatur"},
    {"userId": 3,  "id": 28, "title": "delectus ullam et corporis nulla voluptas sequi", "body": "non et quaerat ex quae ad maiores\nmaiores recusandae totam aut blanditiis mollitia quas illo\nut voluptatibus voluptatem\nsimilique nostrum eum"},
    {"userId": 3,  "id": 29, "title": "iusto eius quod necessitatibus culpa ea", "body": "odit magnam ut saepe sed non qui\ntempora atque nihil\naccusamus illum doloribus illo dolor\neligendi repudiandae odit magni similique sed cum maiores"},
    {"userId": 3,  "id": 30, "title": "a quo magni similique perferendis", "body": "alias dolor cumque\nimpedit blanditiis non eveniet odio maxime\nblanditiis amet eius quis tempora quia autem rem\na provident perspiciatis quia"},
    {"userId": 4,  "id": 31, "title": "ullam ut quidem id aut vel consequuntur", "body": "debitis eius sed quibusdam non quis consectetur vitae\nimpedit ut qui consequatur sed aut in\nquidem sit nostrum et maiores adipisci atque\nquaerat voluptatem adipisci repudiandae"},
    {"userId": 4,  "id": 32, "title": "doloremque illum aliquid sunt", "body": "deserunt eos nobis asperiores et hic\nest debitis repellat molestiae optio\nnihil ratione ut eos beatae quibusdam distinctio maiores\nearum voluptates et aut adipisci ea maiores voluptas maxime"},
    {"userId": 4,  "id": 33, "title": "qui explicabo molestiae dolorem", "body": "rerum ut et numquam laborum odit est sit\nid qui sint in\nquasi tenetur tempore aperiam et quaerat qui in\nrerum officiis sequi cumque quod"},
    {"userId": 4,  "id": 34, "title": "magnam ut rerum iure", "body": "ea velit perferendis earum ut voluptatem voluptate itaque iusto\ntotam pariatur in\nnemo voluptatem voluptatem autem magni tempora minima in\nest distinctio qui assumenda accusamus dignissimos officia nesciunt nobis"},
    {"userId": 4,  "id": 35, "title": "id nihil consequatur molestias animi provident", "body": "nisi error delectus possimus ut eligendi vitae\nplaceat eos harum cupiditate facilis reprehenderit voluptatem beatae\nmodi ducimus quo illum voluptas eligendi\net nobis quia fugit"},
    {"userId": 4,  "id": 36, "title": "fuga nam accusamus voluptas reiciendis itaque", "body": "ad mollitia et omnis minus architecto odit\nvoluptas doloremque maxime aut non ipsa qui alias veniam\nblanditiis culpa aut quia nihil cumque facere et occaecati\nqui aspernatur quia eaque ut aperiam inventore"},
    {"userId": 4,  "id": 37, "title": "provident vel ut sit ratione est", "body": "debitis et eaque non officia sed nesciunt pariatur vel\nvoluptatem iste vero et ea\nnumquam aut expedita ipsum nulla in\nvoluptates omnis consequatur aut enim officiis in quam qui"},
    {"userId": 4,  "id": 38, "title": "explicabo et eos deleniti nostrum ab id repellendus", "body": "animi esse sit aut sit nesciunt assumenda eum voluptas\nquia voluptatibus provident quia necessitatibus ea\nrerum repudiandae quia voluptatem delectus fugit aut id quia\nratione optio eos iusto veniam iure"},
    {"userId": 4,  "id": 39, "title": "eos dolorem iste accusantium est eaque quam", "body": "corporis rerum ducimus vel eum accusantium\nmaxime aspernatur a porro possimus iste omnis\nest in deleniti asperiores fuga aut\nvoluptas sapiente vel dolore minus voluptatem incidunt ex"},
    {"userId": 4,  "id": 40, "title": "enim quo cumque", "body": "ut voluptatum aliquid illo tenetur nemo sequi quo facilis\nipsum rem optio mollitia quas\nvoluptatem eum voluptas qui\nunde omnis voluptatem iure quasi maxime voluptas nam"},
    {"userId": 5,  "id": 41, "title": "non est facere", "body": "molestias id nostrum\nexcepturi molestiae dolore omnis repellendus quaerat saepe\nconsectetur iste quaerat tenetur asperiores accusamus ex ut\nnam quidem est ducimus sunt debitis saepe"},
    {"userId": 5,  "id": 42, "title": "commodi ullam sint et excepturi error explicabo praesentium voluptas", "body": "odio fugit voluptatum ducimus earum autem est incidunt voluptatem\nodit reiciendis aliquam sunt sequi nulla dolorem\nnon facere repellendus voluptates quia\nratione harum vitae ut"},
    {"userId": 5,  "id": 43, "title": "eligendi iste nostrum consequuntur adipisci praesentium sit beatae perferendis", "body": "similique fugit est\nillum et dolorum harum et voluptate eaque quidem\nexercitationem quos nam commodi possimus cum odio nihil nulla\ndolorum exercitationem magnam ex et a et distinctio debitis"},
    {"userId": 5,  "id": 44, "title": "optio dolor molestias sit", "body": "temporibus est consectetur dolore\net libero debitis vel velit laboriosam quia\nipsum quibusdam qui itaque fuga rem aut\nea et iure quam sed maxime ut distinctio quae"},
    {"userId": 5,  "id": 45, "title": "ut numquam possimus omnis eius suscipit laudantium iure", "body": "est natus reiciendis nihil possimus aut provident\nex et dolor\nrepellat pariatur est\nnobis rerum repellendus dolorem autem"},
    {"userId": 5,  "id": 46, "title": "aut quo modi neque nostrum ducimus", "body": "voluptatem quisquam iste\nvoluptatibus natus officiis facilis dolorem\nquis quas ipsam\nvel et voluptatum in aliquid"},
    {"userId": 5,  "id": 47, "title": "quibusdam cumque rem aut deserunt", "body": "voluptatem assumenda ut qui ut cupiditate aut impedit veniam\noccaecati nemo illum voluptatem laudantium\nmolestiae beatae rerum ea iure soluta nostrum\neligendi et voluptate"},
    {"userId": 5,  "id": 48, "title": "ut voluptatem illum ea doloribus itaque eos", "body": "voluptates quo voluptatem facilis iure occaecati\nvel assumenda rerum officia et\nillum perspiciatis ab deleniti\nlaudantium repellat ad ut et autem reprehenderit"},
    {"userId": 5,  "id": 49, "title": "laborum non sunt aut ut assumenda perspiciatis voluptas", "body": "inventore ab sint\nnatus fugit id nulla sequi architecto nihil quaerat\neos tenetur in in eum veritatis non\nquibusdam officiis aspernatur cumque aut commodi aut"},
    {"userId": 5,  "id": 50, "title": "repellendus qui recusandae incidunt voluptates tenetur qui omnis exercitationem", "body": "error suscipit maxime adipisci consequuntur recusandae\nvoluptas eligendi et est et voluptates\nquia distinctio ab amet quaerat molestiae et vitae\nadipisci impedit sequi nesciunt quis consectetur"},
    {"userId": 6,  "id": 51, "title": "soluta aliquam aperiam consequatur illo quis voluptas", "body": "sunt dolores aut doloribus\ndolore doloribus voluptates tempora et\ndoloremque et quo\ncum asperiores sit consectetur dolorem"},
    {"userId": 6,  "id": 52, "title": "qui enim et consequuntur quia animi quis voluptate quibusdam", "body": "iusto est quibusdam fuga quas quaerat molestias\na enim ut sit accusamus enim\ntemporibus iusto accusantium provident architecto\nsoluta esse reprehenderit qui laborum"},
    {"userId": 6,  "id": 53, "title": "ut quo aut ducimus alias", "body": "minima harum praesentium eum rerum illo dolore\nquasi exercitationem rerum nam\nporro quis neque quo\nconsequatur minus dolor quidem veritatis sunt non explicabo similique"},
    {"userId": 6,  "id": 54, "title": "sit asperiores ipsam eveniet odio non quia", "body": "totam corporis dignissimos\nvitae dolorem ut occaecati accusamus\nex velit deserunt\net exercitationem vero incidunt corrupti mollitia"},
    {"userId": 6,  "id": 55, "title": "sit vel voluptatem et non libero", "body": "debitis excepturi ea perferendis harum libero optio\neos accusamus cum fuga ut sapiente repudiandae\net ut incidunt omnis molestiae\nnihil ut eum odit"},
    {"userId": 6,  "id": 56, "title": "qui et at rerum necessitatibus", "body": "aut est omnis dolores\nneque rerum quod ea rerum velit pariatur beatae excepturi\net provident voluptas corrupti\ncorporis harum reprehenderit dolores eligendi"},
    {"userId": 6,  "id": 57, "title": "sed ab est est", "body": "at pariatur consequuntur earum quidem\nquo est laudantium soluta voluptatem\nqui ullam et est\net cum voluptas voluptatum repellat est"},
    {"userId": 6,  "id": 58, "title": "voluptatum itaque dolores nisi et quasi", "body": "veniam voluptatum quae adipisci id\net id quia eos ad et dolorem\naliquam quo nisi sunt eos impedit error\nad similique veniam"},
    {"userId": 6,  "id": 59, "title": "qui commodi dolor at maiores et quis id accusantium", "body": "perspiciatis et quam ea autem temporibus non voluptatibus qui\nbeatae a earum officia nesciunt dolores suscipit voluptas et\nanimi doloribus cum rerum quas et magni\net hic ut ut commodi expedita sunt"},
    {"userId": 6,  "id": 60, "title": "consequatur placeat omnis quisquam quia reprehenderit fugit veritatis facere", "body": "asperiores sunt ab assumenda cumque modi velit\nqui esse omnis\nvoluptate et fuga perferendis voluptas\nillo ratione amet aut et omnis"},
    {"userId": 7,  "id": 61, "title": "voluptatem doloribus consectetur est ut ducimus", "body": "ab nemo optio odio\ndelectus tenetur corporis similique nobis repellendus rerum omnis facilis\nvero blanditiis debitis in nesciunt doloribus dicta dolores\nmagnam minus velit"},
    {"userId": 7,  "id": 62, "title": "beatae enim quia vel", "body": "enim aspernatur illo distinctio quae praesentium\nbeatae alias amet delectus qui voluptate distinctio\nodit sint accusantium autem omnis\nquo molestiae omnis ea eveniet optio"},
    {"userId": 7,  "id": 63, "title": "voluptas blanditiis repellendus animi ducimus error sapiente et suscipit", "body": "enim adipisci aspernatur nemo\nnumquam omnis facere dolorem dolor ex quis temporibus incidunt\nab delectus culpa quo reprehenderit blanditiis asperiores\naccusantium ut quam in voluptatibus voluptas ipsam dicta"},
    {"userId": 7,  "id": 64, "title": "et fugit quas eum in in aperiam quod", "body": "id velit blanditiis\neum ea voluptatem\nmolestiae sint occaecati est eos perspiciatis\nincidunt a error provident eaque aut aut qui"},
    {"userId": 7,  "id": 65, "title": "consequatur id enim sunt et et", "body": "voluptatibus ex esse\nsint explicabo est aliquid cumque adipisci fuga repellat labore\nmolestiae corrupti ex saepe at asperiores et perferendis\nnatus id esse incidunt pariatur"},
    {"userId": 7,  "id": 66, "title": "repudiandae ea animi iusto", "body": "officia veritatis tenetur vero qui itaque\nsint non ratione\nsed et ut asperiores iusto eos molestiae nostrum\nveritatis quibusdam et nemo iusto saepe"},
    {"userId": 7,  "id": 67, "title": "aliquid eos sed fuga est maxime repellendus", "body": "reprehenderit id nostrum\nvoluptas doloremque pariatur sint et accusantium quia quod aspernatur\net fugiat amet\nnon sapiente et consequatur necessitatibus molestiae"},
    {"userId": 7,  "id": 68, "title": "odio quis facere architecto reiciendis optio", "body": "magnam molestiae perferendis quisquam\nqui cum reiciendis\nquaerat animi amet hic inventore\nea quia deleniti quidem saepe porro velit"},
    {"userId": 7,  "id": 69, "title": "fugiat quod pariatur odit minima", "body": "officiis error culpa consequatur modi asperiores et\ndolorum assumenda voluptas et vel qui aut vel rerum\nvoluptatum quisquam perspiciatis quia rerum consequatur totam quas\nsequi commodi repudiandae asperiores et saepe a"},
    {"userId": 7,  "id": 70, "title": "voluptatem laborum magni", "body": "sunt repellendus quae\nest asperiores aut deleniti esse accusamus repellendus quia aut\nquia dolorem unde\neum tempora esse dolore"},
    {"userId": 8,  "id": 71, "title": "et iusto veniam et illum aut fuga", "body": "occaecati a doloribus\niste saepe consectetur placeat eum voluptate dolorem et\nqui quo quia voluptas\nrerum ut id enim velit est perferendis"},
    {"userId": 8,  "id": 72, "title": "sint hic doloribus consequatur eos non id", "body": "quam occaecati qui deleniti consectetur\nconsequatur aut facere quas exercitationem aliquam hic voluptas\nneque id sunt ut aut accusamus\nsunt consectetur expedita inventore velit"},
    {"userId": 8,  "id": 73, "title": "consequuntur deleniti eos quia temporibus ab aliquid at", "body": "voluptatem cumque tenetur consequatur expedita ipsum nemo quia explicabo\naut eum minima consequatur\ntempore cumque quae est et\net in consequuntur voluptatem voluptates aut"},
    {"userId": 8,  "id": 74, "title": "enim unde ratione doloribus quas enim ut sit sapiente", "body": "odit qui et et necessitatibus sint veniam\nmollitia amet doloremque molestiae commodi similique magnam et quam\nblanditiis est itaque\nquo et tenetur ratione occaecati molestiae tempora"},
    {"userId": 8,  "id": 75, "title": "dignissimos eum dolor ut enim et delectus in", "body": "commodi non non omnis et voluptas sit\nautem aut nobis magnam et sapiente voluptatem\net laborum repellat qui delectus facilis temporibus\nrerum amet et nemo voluptate expedita adipisci error dolorem"},
    {"userId": 8,  "id": 76, "title": "doloremque officiis ad et non perferendis", "body": "ut animi facere\ntotam iusto tempore\nmolestiae eum aut et dolorem aperiam\nquaerat recusandae totam odio"},
    {"userId": 8,  "id": 77, "title": "necessitatibus quasi exercitationem odio", "body": "modi ut in nulla repudiandae dolorum nostrum eos\naut consequatur omnis\nut incidunt est omnis iste et quam\nvoluptates sapiente aliquam asperiores nobis amet corrupti repudiandae provident"},
    {"userId": 8,  "id": 78, "title": "quam voluptatibus rerum veritatis", "body": "nobis facilis odit tempore cupiditate quia\nassumenda doloribus rerum qui ea\nillum et qui totam\naut veniam repellendus"},
    {"userId": 8,  "id": 79, "title": "pariatur consequatur quia magnam autem omnis non amet", "body": "libero accusantium et et facere incidunt sit dolorem\nnon excepturi qui quia sed laudantium\nquisquam molestiae ducimus est\nofficiis esse molestiae iste et quos"},
    {"userId": 8,  "id": 80, "title": "labore in ex et explicabo corporis aut quas", "body": "ex quod dolorem ea eum iure qui provident amet\nquia qui facere excepturi et repudiandae\nasperiores molestias provident\nminus incidunt vero fugit rerum sint sunt excepturi provident"},
    {"userId": 9,  "id": 81, "title": "tempora rem veritatis voluptas quo dolores vero", "body": "facere qui nesciunt est voluptatum voluptatem nisi\nsequi eligendi necessitatibus ea at rerum itaque\nharum non ratione velit laboriosam quis consequuntur\nex officiis minima doloremque voluptas ut aut"},
    {"userId": 9,  "id": 82, "title": "laudantium voluptate suscipit sunt enim enim", "body": "ut libero sit aut totam inventore sunt\nporro sint qui sunt molestiae\nconsequatur cupiditate qui iste ducimus adipisci\ndolor enim assumenda soluta laboriosam amet iste delectus hic"},
    {"userId": 9,  "id": 83, "title": "odit et voluptates doloribus alias odio et", "body": "est molestiae facilis quis tempora numquam nihil qui\nvoluptate sapiente consequatur est qui\nnecessitatibus autem aut ipsa aperiam modi dolore numquam\nreprehenderit eius rem quibusdam"},
    {"userId": 9,  "id": 84, "title": "optio ipsam molestias necessitatibus occaecati facilis veritatis dolores aut", "body": "sint molestiae magni a et quos\neaque et quasi\nut rerum debitis similique veniam\nrecusandae dignissimos dolor incidunt consequatur odio"},
    {"userId": 9,  "id": 85, "title": "dolore veritatis porro provident adipisci blanditiis et sunt", "body": "similique sed nisi voluptas iusto omnis\nmollitia et quo\nassumenda suscipit officia magnam sint sed tempora\nenim provident pariatur praesentium atque animi amet ratione"},
    {"userId": 9,  "id": 86, "title": "placeat quia et porro iste", "body": "quasi excepturi consequatur iste autem temporibus sed molestiae beatae\net quaerat et esse ut\nvoluptatem occaecati et vel explicabo autem\nasperiores pariatur deserunt optio"},
    {"userId": 9,  "id": 87, "title": "nostrum quis quasi placeat", "body": "eos et molestiae\nnesciunt ut a\ndolores perspiciatis repellendus repellat aliquid\nmagnam sint rem ipsum est"},
    {"userId": 9,  "id": 88, "title": "sapiente omnis fugit eos", "body": "consequatur omnis est praesentium\nducimus non iste\nneque hic deserunt\nvoluptatibus veniam cum et rerum sed"},
    {"userId": 9,  "id": 89, "title": "sint soluta et vel magnam aut ut sed qui", "body": "repellat aut aperiam totam temporibus autem et\narchitecto magnam ut\nconsequatur qui cupiditate rerum quia soluta dignissimos nihil iure\ntempore quas est"},
    {"userId": 9,  "id": 90, "title": "ad iusto omnis odit dolor voluptatibus", "body": "minus omnis soluta quia\nqui sed adipisci voluptates illum ipsam voluptatem\neligendi officia ut in\neos soluta similique molestias praesentium blanditiis"},
    {"userId": 10, "id": 91, "title": "aut amet sed", "body": "libero voluptate eveniet aperiam sed\nsunt placeat suscipit molestias\nsimilique fugit nam natus\nexpedita consequatur consequatur dolores quia eos et placeat"},
    {"userId": 10, "id": 92, "title": "ratione ex tenetur perferendis", "body": "aut et excepturi dicta laudantium sint rerum nihil\nlaudantium et at\na neque minima officia et similique libero et\ncommodi voluptate qui"},
    {"userId": 10, "id": 93, "title": "beatae soluta recusandae", "body": "dolorem quibusdam ducimus consequuntur dicta aut quo laboriosam\nvoluptatem quis enim recusandae ut sed sunt\nnostrum est odit totam\nsit error sed sunt eveniet provident qui nulla"},
    {"userId": 10, "id": 94, "title": "qui qui voluptates illo iste minima", "body": "aspernatur expedita soluta quo ab ut similique\nexpedita dolores amet\nsed temporibus distinctio magnam saepe deleniti\nomnis facilis nam ipsum natus sint similique omnis"},
    {"userId": 10, "id": 95, "title": "id minus libero illum nam ad officiis", "body": "earum voluptatem facere provident blanditiis velit laboriosam\npariatur accusamus odio saepe\ncumque dolor qui a dicta ab doloribus consequatur omnis\ncorporis cupiditate eaque assumenda ad nesciunt"},
    {"userId": 10, "id": 96, "title": "quaerat velit veniam amet cupiditate aut numquam ut sequi", "body": "in non odio excepturi sint eum\nlabore voluptates vitae quia qui et\ninventore itaque rerum\nveniam non exercitationem delectus aut"},
    {"userId": 10, "id": 97, "title": "quas fugiat ut perspiciatis vero provident", "body": "eum non blanditiis soluta porro quibusdam voluptas\nvel voluptatem qui placeat dolores qui velit aut\nvel inventore aut cumque culpa explicabo aliquid at\nperspiciatis est et voluptatem dignissimos dolor itaque sit nam"},
    {"userId": 10, "id": 98, "title": "laboriosam dolor voluptates", "body": "doloremque ex facilis sit sint culpa\nsoluta assumenda eligendi non ut eius\nsequi ducimus vel quasi\nveritatis est dolores"},
    {"userId": 10, "id": 99, "title": "temporibus sit alias delectus eligendi possimus magni", "body": "quo deleniti praesentium dicta non quod\naut est molestias\nmolestias et officia quis nihil\nitaque dolorem quia"},
    {"userId": 10, "id": 100, "title": "at nam consequatur ea labore ea harum", "body": "cupiditate quo est a modi nesciunt soluta\nipsa voluptas error itaque dicta in\nautem qui minus magnam et distinctio eum\naccusamus ratione error aut"},
]


# ── Screenshot ─────────────────────────────────────────────────────────────────

def take_screenshot() -> tuple[Image.Image, bytes]:
    """Capture full desktop. Returns (PIL Image resized to ≤1280px wide, JPEG bytes)."""
    with mss.MSS() as sct:
        raw = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if img.width > 1280:
        img = img.resize((1280, int(img.height * 1280 / img.width)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return img, buf.getvalue()


# ── Vision (OpenRouter) ────────────────────────────────────────────────────────

def ask_vision(image_bytes: bytes, question: str) -> str:
    """Send image + question to vision model via OpenRouter."""
    import base64
    image_b64 = base64.standard_b64encode(image_bytes).decode()
    try:
        response = client.chat.send(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": question},
                ],
            }],
            max_tokens=256,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        if "free-models-per-day" in str(e) or "TooManyRequests" in type(e).__name__:
            print("  [Vision] Daily free limit reached — add credits at openrouter.ai/credits")
        else:
            print(f"  [Vision] Error: {e}")
        return ""


def find_icon(description: str) -> tuple[int, int] | None:
    """
    Ask vision model to locate an icon/element on the desktop.
    Works for any icon regardless of position, theme, or background.
    Returns pixel (x, y) center coordinates, or None if not found.
    """
    img, image_bytes = take_screenshot()

    prompt = (
        f"Look at this Windows desktop screenshot. Find: {description}\n\n"
        "Reply with ONLY a JSON object, nothing else:\n"
        '  If found:   {"found": true, "x": 0.35, "y": 0.22}\n'
        '  If missing: {"found": false}\n\n'
        "x and y are the CENTER of the target as a FRACTION of image size "
        "(0.0 = left/top edge, 1.0 = right/bottom edge).\n"
        "Be precise — this will be used to click the exact center of the icon."
    )

    raw = ask_vision(image_bytes, prompt).strip("` \n").removeprefix("json").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [Vision] Could not parse JSON: {raw!r}")
        return None

    if not data.get("found"):
        print(f"  [Vision] '{description}' not found in screenshot")
        return None

    x = int(data["x"] * img.width)
    y = int(data["y"] * img.height)
    print(f"  [Vision] Found '{description}' at ({data['x']:.2f}, {data['y']:.2f}) → pixel ({x}, {y})")

    return x, y


def handle_popup() -> bool:
    """
    Ask vision model if any unexpected pop-up or dialog is visible.
    If yes, click its dismiss/OK/Close button automatically.
    Returns True if a pop-up was handled.
    """
    img, image_bytes = take_screenshot()

    prompt = (
        "Look at this Windows desktop screenshot.\n"
        "Is there any pop-up dialog, warning box, or modal window open "
        "(other than Notepad's main window)?\n\n"
        "Reply ONLY with JSON:\n"
        '  Pop-up present: {"popup": true, "button": "OK", "x": 0.5, "y": 0.6}\n'
        '  No pop-up:      {"popup": false}\n\n'
        "x and y are the CENTER of the button to click as fractions of image size.\n"
        "'button' is the label of the button you would click to dismiss it."
    )

    raw = ask_vision(image_bytes, prompt).strip("` \n").removeprefix("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False

    if data.get("popup"):
        x = int(data["x"] * img.width)
        y = int(data["y"] * img.height)
        btn = data.get("button", "?")
        print(f"  [Vision] Pop-up detected — clicking '{btn}' at ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(0.5)
        return True

    return False


# ── Data ───────────────────────────────────────────────────────────────────────

def fetch_posts() -> list[dict]:
    import requests
    try:
        r = requests.get(
            "https://jsonplaceholder.typicode.com/posts",
            params={"_limit": 3},
            timeout=10,
        )
        r.raise_for_status()
        posts = r.json()
        print(f"Fetched {len(posts)} posts from JSONPlaceholder API")
        return posts
    except Exception as exc:
        print(f"JSONPlaceholder API unavailable ({exc.__class__.__name__}) — using local copy")
        return FALLBACK_POSTS[:3]


# ── Notepad Automation ─────────────────────────────────────────────────────────

def open_notepad() -> bool:
    """
    Show desktop, ground the Notepad icon with Gemini, double-click it.
    Retries up to 3 times with 1s delay (as per task spec).
    Falls back to subprocess launch if vision grounding fails.
    """
    pyautogui.hotkey("win", "d")
    time.sleep(0.8)

    coords = None
    for attempt in range(1, 4):
        print(f"  Detection attempt {attempt}/3...")
        coords = find_icon("notepad.exe shortcut icon on the Windows desktop")
        if coords:
            break
        time.sleep(1)

    if coords:
        pyautogui.doubleClick(*coords)
        print(f"  Clicked Notepad at {coords}")
    else:
        print("  Icon not found after 3 attempts — launching Notepad directly")
        subprocess.Popen("notepad.exe")

    # Wait for Notepad window (up to 10s)
    deadline = time.time() + 10
    while time.time() < deadline:
        windows = gw.getWindowsWithTitle("Notepad")
        if windows:
            windows[0].activate()
            time.sleep(0.3)
            return True
        # Check for unexpected pop-up blocking launch
        handle_popup()
        time.sleep(0.5)

    return False


def write_and_save(title: str, body: str, post_id: int) -> Path:
    save_path = SAVE_DIR / f"post_{post_id}.txt"

    # Paste content (handles unicode safely)
    pyperclip.copy(f"Title: {title}\n\n{body}")
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)

    # Open Save As dialog and wait for it to fully render
    pyautogui.hotkey("ctrl", "shift", "s")
    time.sleep(2.0)

    # Focus the filename field explicitly (Alt+N moves focus to "File name:" box
    # in the standard Windows Save As dialog) then select-all and paste full path
    pyautogui.hotkey("alt", "n")
    time.sleep(0.2)
    pyperclip.copy(str(save_path))
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
    pyautogui.press("enter")  # navigate to directory / confirm filename
    time.sleep(1.0)
    pyautogui.press("enter")  # confirm overwrite if file already exists
    time.sleep(0.5)

    # Windows 11 Notepad may show an encoding dialog ("Save as type" / encoding)
    # — dismiss it by pressing Enter (accepting the default UTF-8 encoding)
    windows = gw.getWindowsWithTitle("Notepad")
    if not windows:
        # No Notepad window means Save As succeeded; nothing more to do
        return save_path
    # Check for an encoding or extra confirmation dialog still open
    extra_dialogs = [w for w in gw.getAllWindows()
                     if w.title and w.title not in ("", "Notepad") and "Notepad" in w.title]
    if extra_dialogs:
        pyautogui.press("enter")
        time.sleep(0.5)

    return save_path


def close_notepad() -> None:
    pyautogui.hotkey("alt", "f4")
    time.sleep(1.2)

    # Primary: use the keyboard accelerator for "Don't Save".
    # Windows message-box buttons expose their underlined letter via Alt+<key>.
    # "Don't Save" → Alt+N (the 't' in "Don'T save" on older Notepad,
    # or the 'N' shortcut on Windows 11 Notepad's dialog).
    # We try both; only the active one will fire.
    pyautogui.hotkey("alt", "n")
    time.sleep(0.3)

    # Fallback: if the dialog is still up, use vision to click "Don't Save"
    windows_open = gw.getWindowsWithTitle("Notepad")
    if windows_open:
        img, image_bytes = take_screenshot()
        prompt = (
            "Look at this screenshot. Is there a Notepad 'Do you want to save' dialog visible?\n"
            "Reply ONLY with JSON:\n"
            '  Dialog present: {"dialog": true, "x": 0.5, "y": 0.55}\n'
            '  No dialog:      {"dialog": false}\n'
            "x and y are the center of the \"Don't Save\" or \"No\" button as fractions of image size."
        )
        raw = ask_vision(image_bytes, prompt).strip("` \n").removeprefix("json").strip()
        try:
            data = json.loads(raw)
            if data.get("dialog"):
                x = int(data["x"] * img.width)
                y = int(data["y"] * img.height)
                print(f"  [Vision] Save dialog detected — clicking Don't Save at ({x}, {y})")
                pyautogui.click(x, y)
                time.sleep(0.5)
        except json.JSONDecodeError:
            pass


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort

    posts = fetch_posts()
    ok = 0

    for post in posts:
        print(f"\n── Post {post['id']}: {post['title'][:55]} ──")

        if not open_notepad():
            print("  Notepad did not open — skipping this post")
            continue

        path = write_and_save(post["title"], post["body"], post["id"])
        print(f"  Saved → {path}")

        close_notepad()
        ok += 1
        time.sleep(0.5)

    print(f"\nDone. {ok}/{len(posts)} posts saved to {SAVE_DIR}")



if __name__ == "__main__":
    main()
