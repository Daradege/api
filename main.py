from flask import Flask, request, jsonify, send_file, Response
import io
import random
import bs4
import requests
import qrcode
import socket
import ipaddress
import json
from googlesearch import search
from flask_cors import CORS
import aparat
import base64
import feedparser
import datetime
import jdatetime
from ping3 import ping
from urllib.parse import urlparse
import certifi
import ssl
from dotenv import load_dotenv
import os
import asyncio
import edge_tts

load_dotenv()
env = os.getenv

holiday_api = "https://holidayapi.ir/jalali/"
time_now_api = "https://api.keybit.ir/time/"
HF_TOKEN = env("HUGGINGFACE_TOKEN")
OPENROUTER_API_KEY = env("OPENROUTER_TOKEN")
MAJIDAPI_TOKEN = env("MAJIDAPI_TOKEN")
CODEBAZAN_TOKEN = env("CODEBAZAN_TOKEN")
FASTCREAT_TOKEN = env("FASTCREAT_TOKEN")

aparatclient = aparat.Aparat()

app = Flask(__name__, static_url_path='/static')

decoded_secret_key = env("SECRET_KEY")
app.secret_key = base64.b64decode(decoded_secret_key)

cors = CORS(app, origins=["*"])

translator_suppoted_langs = ["de", "en", "fa", "tr", "ar", "fr", "nl", "zh"]


def get_faal_hafez():
    api = "https://api-free.ir/api/fal"
    res = requests.get(api).json()
    urlt = res["result"]
    return requests.get(urlt).read()


def get_shari_owghat(text: str):
    api = "https://api.keybit.ir/owghat/?city="
    res = requests.get(api + text).json()
    try:
        return res["result"]
    except BaseException:
        return "شهر یافت نشد"


def translate_to_english(text: str):
    try:
        html = requests.get(
            f"https://api.fast-creat.ir/translate?apikey={FASTCREAT_TOKEN}&text={text}&to=en").json()
        return html["result"]["translate"]
    except BaseException:
        return "some errors from api"


def translate_to_any_lang(text: str, to: str):
    try:
        html = requests.get(
            f"https://api.fast-creat.ir/translate?apikey={FASTCREAT_TOKEN}&text={text}&to={to}").json()
        return html["result"]["translate"]
    except BaseException:
        return "some errors from api"


def fetch_weather(city):
    url = "https://api.codesazan.ir/Weather/"
    params = {
        'key': '',
        'type': 'Weather',
        'city': city,
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if "result" in data:
                return data["result"]
        return None
    except (requests.RequestException, json.JSONDecodeError):
        return None


async def tts_base(TEXT="Hi", VOICE="fa-IR-FaridNeural") -> bytes:
    communicate = edge_tts.Communicate(TEXT, VOICE)
    audio_data = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
    return bytes(audio_data)


def get_audio(text: str):
    return asyncio.run(tts_base(text))

def get_aparat_vid(hash="guvp1s7"):
    vid = aparatclient.video(hash)
    return {attr: getattr(vid, attr)
            for attr in dir(vid) if not attr.startswith('_')}


def google(q): return search(q, num_results=10, advanced=True)


def time_now():
    return requests.get(time_now_api).json()


def get_holiday(date):
    return requests.get(holiday_api + date).json()


def get_owghat(city="تهران"):
    return requests.get(
        f"https://api.daradege.ir/owghat?city={city}").json()['owghat']


def get_ping(host):
    result = ping(host, timeout=2)
    return f"{result * 1000:.2f} ms" if result else "Timeout / Unreachable"


def get_data_from_id(uid):
    url = "https://ble.ir/" + uid
    response = requests.get(url)
    if response.status_code != 200:
        return {"status": "error", "error": "request failed"}

    req = response.text
    if """<p class="__404_title__lxIKL">گفتگوی مورد نظر وجود ندارد.</p>""" in req:
        return {"status": "error", "error": "not found"}

    soup = bs4.BeautifulSoup(req, "html.parser")
    data = {
        "status": "success",
        "avatar": None,
        "description": None,
        "name": None,
        "is_bot": False,
        "is_verified": False,
        "is_private": False,
        "members": None,
        "last_message": None,
        "user_id": None,
        "username": None
    }

    try:
        data["avatar"] = soup.find("img", class_="Avatar_img___C2_3")["src"]
        data["description"] = soup.find(
            "div", class_="Profile_description__YTAr_").text
        data["name"] = soup.find("h1", class_="Profile_name__pQglx").text
    except BaseException:
        pass

    try:
        json_data = json.loads(soup.find("script", id="__NEXT_DATA__").text)
        page_props = json_data["props"]["pageProps"]

        entity = page_props.get("user") or page_props.get("group") or {}
        data["is_bot"] = entity.get("isBot", False)
        data["is_verified"] = entity.get("isVerified", False)
        data["is_private"] = entity.get("isPrivate", False)
        data["members"] = page_props.get("group", {}).get("members")
        data["user_id"] = page_props.get("peer", {}).get("id")
        data["username"] = page_props.get("user", {}).get("nick")

        messages = page_props.get("messages", [])
        if messages:
            last_msg = messages[-1].get("message", {})
            data["last_message"] = (
                last_msg.get("documentMessage", {}).get("caption", {}).get("text") or
                last_msg.get("textMessage", {}).get("text")
            )
            if data["last_message"]:
                data["last_message"] = data["last_message"].replace(
                    "&zwnj;", "")
    except BaseException:
        pass

    return data


def get_request_data():
    """Extract data from both GET and POST requests"""
    if request.method == 'POST':
        data = request.get_json() or {}
        return data.get("text"), data.get("lang"), data.get("city")
    return request.args.get("text"), request.args.get(
        "lang"), request.args.get("city")


@app.errorhandler(500)
def internal_error(error):
    return jsonify(
        {"error": "Internal Server Error, Call the support (https://t.me/daradege https://ble.ir/daradege)"}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404


@app.route("/", methods=["GET"])
def home():
    return open("mainpage.html", encoding="utf-8").read()


@app.route("/aimagic.jpg", methods=["GET", "POST"])
def aimagic():
    return send_file("static/aimagic.jpg", mimetype="image/jpeg")


@app.route('/manifest.json', methods=["GET", "POST"])
def manifest():
    return send_file("static/manifest.json", mimetype="application/json")


@app.route('/service-worker.js', methods=["GET", "POST"])
def service_worker():
    return send_file("static/service-worker.js", mimetype="text/javascript")


@app.route("/tts", methods=["GET", "POST"])
def tts():
    """Text-to-Speech endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No text provided", 400
    audio = get_audio(text)
    return Response(audio, mimetype="audio/mpeg")


@app.route("/image", methods=["GET", "POST"])
def image():
    """Image generation endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No text provided", 400

    url = f"https://image.pollinations.ai/prompt/{text}"
    params = {
        "width": 1024,
        "height": 1024,
        "seed": random.randint(1, 100000000000),
        "model": "flux",
        "nologo": "true"
    }

    session = requests.Session()
    response = session.get(url, params=params)
    if response.status_code != 200:
        return jsonify({"error": "Failed to generate image"}
                       ), response.status_code
    return Response(response.content, mimetype="image/jpeg")


@app.route("/logo", methods=["GET", "POST"])
def logo():
    """Logo generation endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No text provided", 400

    url = f"https://image.pollinations.ai/prompt/a%20logo%20for%20{text}"
    params = {
        "width": 1024,
        "height": 1024,
        "seed": random.randint(1, 100000000000),
        "model": "flux-pro",
        "nologo": "true"
    }

    session = requests.Session()
    response = session.get(url, params=params)
    if response.status_code != 200:
        return jsonify({"error": "Failed to generate image"}
                       ), response.status_code
    return Response(response.content, mimetype="image/jpeg")


@app.route("/ai", methods=["GET", "POST"])
def ai():
    """AI chat endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No text provided", 400
    api_url = f"https://api.majidapi.ir/gpt/35?q={text}&token={MAJIDAPI_TOKEN}"
    result = requests.get(api_url).json()['result']

    return jsonify({"text": result})


def process_openrouter_request(text, model, history=[]):
    """Helper function to process OpenRouter API requests"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://api.daradege.ir",
        "X-Title": "api.daradege.ir",
    }
    messages = history + [{"role": "user", "content": text}]
    data = {
        "model": model,
        "messages": messages
    }

    session = requests.Session()
    response = session.post(url, headers=headers, json=data)
    if response.status_code != 200:
        return jsonify(
            {"error": "Failed to process request. Call Support (check website's the footer)"}), response.status_code
    result = response.json()
    return jsonify({"text": result["choices"][0]["message"]["content"]})


@app.route("/deepseek", methods=["GET", "POST"])
def deepseek():
    """DeepSeek model endpoint"""
    text, _, _ = get_request_data()
    if request.method == "POST":
        history = request.get_json().get("history", [])
    else:
        history = []

    if not text:
        return "No text provided", 400
    if not history:
        return process_openrouter_request(
            text, "deepseek/deepseek-chat-v3-0324:free")
    return process_openrouter_request(
        text, "deepseek/deepseek-chat-v3-0324:free", history)


@app.route("/qwen", methods=["GET", "POST"])
def qwen():
    """Qwen model endpoint"""
    text, _, _ = get_request_data()
    if request.method == "POST":
        history = request.get_json().get("history", [])
    else:
        history = []
    if not text:
        return "No text provided", 400
    if not history:
        return process_openrouter_request(
            text, "qwen/qwen2.5-vl-72b-instruct:free")
    return process_openrouter_request(
        text, "qwen/qwen2.5-vl-72b-instruct:free", history)


@app.route("/llama", methods=["GET", "POST"])
def llama():
    """LLaMA model endpoint"""
    text, _, _ = get_request_data()
    if request.method == "POST":
        history = request.get_json().get("history", [])
    else:
        history = []
    if not text:
        return "No text provided", 400
    if not history:
        return process_openrouter_request(
            text, "meta-llama/llama-4-maverick:free")
    return process_openrouter_request(
        text, "meta-llama/llama-4-maverick:free", history)


@app.route("/nemotron", methods=["GET", "POST"])
def nemotron():
    """NemoTron model endpoint"""
    text, _, _ = get_request_data()
    if request.method == "POST":
        history = request.get_json().get("history", [])
    else:
        history = []
    if not text:
        return "No text provided", 400
    if not history:
        return process_openrouter_request(
            text, "nvidia/llama-3.3-nemotron-super-49b-v1:free")
    return process_openrouter_request(
        text, "nvidia/llama-3.3-nemotron-super-49b-v1:free", history)


@app.route("/aqi", methods=["GET", "POST"])
def aqi():
    """Air Quality Index endpoint"""
    url = "https://airnow.tehran.ir"
    ids = 'ContentPlaceHolder1_lblAqi3h'

    session = requests.Session()
    response = session.get(url)
    content = response.text
    soup = bs4.BeautifulSoup(content, 'html.parser')
    try:
        aqi_value = soup.find_all('span', {'id': ids})[0].text
        return jsonify({"aqi": aqi_value})
    except IndexError:
        return jsonify({"error": "AQI data not found"}), 404


@app.route("/translate", methods=["GET", "POST"])
def translate():
    """Translation endpoint"""
    text, lang, _ = get_request_data()
    if not text:
        return "No text provided", 400
    if not lang:
        return "No language provided", 400
    if lang not in translator_suppoted_langs:
        return f"Invalid language; supported langs: {' '.join(translator_suppoted_langs)}", 400
    result = translate_to_any_lang(text, lang)
    return jsonify({"text": result})


API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}


def query(file: bytes) -> dict:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    data = file.read()
    headers["Content-Type"] = "audio/wav"
    response = requests.post(API_URL, headers=headers, data=data, verify=False)
    print(response.text)
    s = response.json()
    return s["text"]


@app.route("/speechtotext", methods=["GET", "POST"])
def speechtotext():
    """Speech to text endpoint"""
    if request.method == "POST":
        file = request.files.get("file")
    else:
        return jsonify({"error": "This API only supports POST method"}), 405
    if not file:
        return "No file provided", 400
    try:
        text = query(file)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_directurl_data", methods=["GET", "POST"])
def get_directurl_data():
    """Get file size endpoint"""
    if request.method == "POST":
        data = request.get_json() or {}
        url = data.get("url")
    else:
        url = request.args.get("url")
    if not url:
        return "No URL provided", 400
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        headers = response.headers

        size = headers.get("Content-Length")
        if size:
            size = int(size)
        else:
            size = None

        return jsonify({
            "url": url,
            "size_bytes": size,
            "size_kilobytes": round(size / 1024, 2) if size else None,
            "size_megabytes": round(size / (1024 * 1024), 2) if size else None,
            "content_type": headers.get("Content-Type"),
            "file_name": extract_filename(headers),
            "last_modified": headers.get("Last-Modified"),
            "accept_ranges": headers.get("Accept-Ranges"),
            "server": headers.get("Server"),
            "date": headers.get("Date")
        })

    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500


def extract_filename(headers):
    content_disp = headers.get("Content-Disposition")
    if content_disp and "filename=" in content_disp:
        filename = content_disp.split("filename=")[-1].strip('"')
        return filename
    return None


@app.route("/textfont", methods=["GET", "POST"])
def textfont():
    """Text font styling endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No text provided", 400

    api = f"https://api-free.ir/api/font.php?en="

    req = requests.get(api + text).json()
    font = random.choice(req["result"])

    return jsonify({"text": font})


@app.route("/weather", methods=["GET", "POST"])
def weather():
    """Weather information endpoint"""
    _, _, city = get_request_data()
    if not city:
        return "No city provided", 400
    result = fetch_weather(city)
    return jsonify({"weather": result})


@app.route("/owghat", methods=["GET", "POST"])
def owghat():
    """Prayer times endpoint"""
    _, _, city = get_request_data()
    if not city:
        return "No city provided", 400
    result = get_shari_owghat(city)
    return jsonify({"owghat": result})


@app.route("/faal", methods=["GET", "POST"])
def faal():
    """Faal Hafez endpoint"""
    faal = get_faal_hafez()
    return send_file(io.BytesIO(faal), mimetype='image/jpeg')


@app.route("/joke", methods=["GET", "POST"])
def joke():
    """Joke endpoint"""
    r = requests.get(
        f"https://api.majidapi.ir/fun/joke?token={MAJIDAPI_TOKEN}")
    joke_ = r.json()['result']

    if request.method == 'GET':
        type = request.args.get('type')
    if request.method == 'POST':
        type = request.get_json().get('type')

    if type == 'text':
        return joke_
    return jsonify({"joke": joke_})


@app.route("/danestani", methods=["GET", "POST"])
def danestani():
    """Danestani endpoint"""
    url = f"https://api.majidapi.ir/fun/danestani?token={MAJIDAPI_TOKEN}"
    return jsonify(
        {"status": "success", "data": requests.get(url).json().get("result")})


@app.route("/ip", methods=["GET", "POST"])
def ip():
    """IP address endpoint"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    try:
        hostname = socket.gethostbyaddr(client_ip)[0]
    except BaseException:
        hostname = None

    ip_info = requests.get(f"https://ipwho.is/{client_ip}").json()

    if ip_info.get("success"):
        return jsonify({
            "ip": client_ip,
            "hostname": hostname,
            "version": ip_info["type"],
            "is_private": ipaddress.ip_address(client_ip).is_private,
            "city": ip_info["city"],
            "region": ip_info["region"],
            "region_code": ip_info["region_code"],
            "country": ip_info["country"],
            "country_code": ip_info["country_code"],
            "continent": ip_info["continent"],
            "continent_code": ip_info["continent_code"],
            "latitude": ip_info["latitude"],
            "longitude": ip_info["longitude"],
            "postal": ip_info["postal"],
            "calling_code": ip_info["calling_code"],
            "capital": ip_info["capital"],
            "borders": ip_info["borders"],
            "flag": ip_info["flag"],
            "connection": ip_info["connection"],
            "timezone": ip_info["timezone"]
        })
    else:
        return jsonify({
            "ip": client_ip,
            "hostname": hostname,
            "is_private": ipaddress.ip_address(client_ip).is_private,
            "version": "IPv4" if "." in client_ip else "IPv6",
            "raw_ip": client_ip
        })


@app.route("/whois", methods=["GET", "POST"])
def whois_endpoint():
    """WHOIS lookup endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No domain provided", 400
    url = "https://rasanika.com/api/w/whois?domain=" + text
    response = requests.get(url)
    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch WHOIS data"}
                       ), response.status_code
    return jsonify(response.json())


@app.route("/qrcode", methods=["GET", "POST"])
def generate_qrcode():
    """QR Code generation endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No text provided", 400

    fill_color = request.args.get("fill_color", "black")
    back_color = request.args.get("back_color", "white")
    box_size = int(request.args.get("box_size", "10"))
    border = int(request.args.get("border", "2"))

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border
    )
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color=fill_color,
        back_color=back_color
    )

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')


@app.route("/google", methods=["GET", "POST"])
def google_search():
    """Google search endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No search query provided", 400
    l = []
    s = search(text, num_results=15, advanced=True)
    for x in s:
        l.append(
            {
                "title": x.title,
                "url": x.url,
            }
        )
    return jsonify(l)


@app.route("/aparat", methods=["GET", "POST"])
def aparat_video():
    if request.method == "POST":
        video = request.get_json().get("video")
        if not video:
            return jsonify({'error': "No video hash provided"}), 400
    elif request.method == "GET":
        video = request.args.get("video")
        if not video:
            return jsonify({'error': "No video hash provided"}), 400
    try:
        video = get_aparat_vid(video)
        if not video:
            return jsonify({'error': "provided video not found"}), 404
        return jsonify(video)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/aparatsearch-video", methods=["GET", "POST"])
def aparat_search():
    if request.method == "POST":
        text = request.get_json().get("text")
        if not text:
            return jsonify({'error': "No search query provided"}), 400
    elif request.method == "GET":
        text = request.args.get("text")
        if not text:
            return jsonify({'error': "No search query provided"}), 400
    list_ = []
    try:
        videos_list = aparatclient.videoBySearch(text)
        for video in videos_list:
            h = {}
            for attr in dir(video):
                if not attr.startswith('__'):
                    value = getattr(video, attr)
                    if not callable(value):
                        h[attr] = value
            list_.append(h)
        return jsonify(list_)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/searchsong", methods=["GET", "POST"])
def search_song():
    """Song search endpoint"""
    text, _, _ = get_request_data()
    if not text:
        return "No search query provided", 400

    if request.method == "POST":
        mode = request.get_json().get("mode")
    elif request.method == "GET":
        mode = request.args.get("mode")

    if not mode:
        mode = "default"

    search_results = google(text)
    if not search_results:
        return jsonify({"error": "No results found"}), 404

    skip_domains = [
        'youtube.com',
        'spotify.com',
        'soundcloud.com',
        'shazam.com',
        'apple.com',
        'music.apple.com']
    found_sources = []

    for result in search_results:
        if any(domain in result.url.lower() for domain in skip_domains):
            continue

        try:
            page = requests.get(
                result.url, timeout=5, verify=False, headers={
                    'User-Agent': 'Mozilla/5.0'})
            if not page.ok:
                continue

            soup = bs4.BeautifulSoup(page.content, "html.parser")
            songs = soup.find_all("audio")

            for song in songs:
                if song.has_attr('src'):
                    found_sources.append(
                        {"url": song["src"], "source_page": result.url})
                elif song.has_attr('data-src'):
                    found_sources.append(
                        {"url": song["data-src"], "source_page": result.url})

                sources = song.find_all("source")
                for source in sources:
                    if source.has_attr('src'):
                        found_sources.append(
                            {"url": source["src"], "source_page": result.url})
                        if mode == "first":
                            return jsonify(
                                {"results": [{"url": source["src"], "source_page": result.url}]})

        except (requests.exceptions.RequestException, AttributeError):
            continue

    if found_sources:
        if mode == "random":
            return jsonify({"results": [random.choice(found_sources)]})
        elif mode.isdigit():
            num = int(mode)
            return jsonify({"results": found_sources[:num]})
        return jsonify({"results": found_sources})
    return jsonify({"error": "No audio sources found"}), 404


@app.route("/ping", methods=["GET", "POST"])
def ping_view():
    """Ping endpoint"""
    text = request.get_json().get(
        "host") if request.method == "POST" else request.args.get("host")
    domain = text.replace("https://", "").replace("http://", "").split("/")[0]

    if not domain:
        return "No host domain provided", 400

    try:
        data = {
            "host": domain,
            "ping": get_ping(domain)
        }
    except BaseException:
        data = {
            "status": "error",
            "message": "Failed to ping host"
        }
    return jsonify(data)


@app.route("/nameniko", methods=["GET", "POST"])
def nameniko():
    """Nameiko endpoint"""
    name = request.get_json().get(
        "name") if request.method == "POST" else request.args.get("name")

    if not name:
        return "No name provided", 400

    try:
        page = requests.get(f"https://nameniko.com/name/{name}")
        soup = bs4.BeautifulSoup(page.content, "html.parser")

        meaning = soup.find(
            "div", {
                "class": "meaning border-d-white"}).text.strip()
        meaning = ' '.join(meaning.split())

        info_cells = soup.find_all(
            "td", {
                "class": [
                    "r-value color-blue", "r-value color-blue dir-ltr", "r-value num color-blue"]})

        data = {
            "name": name,
            "meaning": meaning,
            "gender": info_cells[0].text.strip().replace("🧑 ", ""),
            "english": info_cells[1].text.strip().replace("🆎", ""),
            "in_iran": int(info_cells[2].text.strip().replace("👶 ", "")),
            "in_persian": info_cells[3].text.strip().replace("📣 ", ""),
            "abjad": info_cells[4].text.strip().replace("🔢 ", ""),
            "pronunciation": info_cells[5].text.strip(),
            "tree": info_cells[6].text.strip().replace("🌍 ", ""),
            "verified": "✅" in info_cells[7].text.strip(),
            "tags": [tag.text.strip() for tag in soup.find("div", {"class": "tags"}).find_all("a")],
            "sabte_ahval_meaning": soup.find("div", {"class": "civil-meaning-text"}).text.strip(),
            "like_name": [name.text.strip() for name in soup.find("div", {"class": "swiper-wrapper"}).find_all("a")]
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": "Name not found"}), 404


@app.route('/news', methods=['GET', 'POST'])
def news():
    """News endpoint"""
    source = request.get_json().get(
        "source") if request.method == "POST" else request.args.get("source")
    mode = request.get_json().get(
        "mode") if request.method == "POST" else request.args.get("mode", "rss")

    if not source:
        return jsonify({'error': "No source provided"}), 400

    NEWS_SOURCES = {
        "isna": "https://www.isna.ir/rss",
        "irna": "https://www.irna.ir/rss",
        "irib": "https://www.iribnews.ir/fa/rss/allnews",
        "mehrnews": "https://mehrnews.com/rss",
        "tasnim": "https://www.tasnimnews.com/fa/rss/feed/0/8/0/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D8%AE%D8%A8%D8%B1%D9%87%D8%A7%DB%8C-%D8%B1%D9%88%D8%B2",
        "digiato": "http://digiato.com/feed",
        "rooziato": "https://rooziato.com/feed",
        "zoomit": "https://www.zoomit.ir/feed"
    }

    if source not in NEWS_SOURCES:
        return jsonify({'error': "Invalid source"}), 400

    if mode not in ['rss', 'json']:
        return jsonify({'error': "Invalid mode"}), 400

    try:
        response = requests.get(NEWS_SOURCES[source])
        if response.status_code != 200:
            return jsonify({'error': "Failed to fetch news"}), 500

        if mode == 'rss':
            return response.text, 200, {'Content-Type': 'application/xml'}

        feed = feedparser.parse(NEWS_SOURCES[source])
        news_list = [{
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary
        } for entry in feed.entries]

        return jsonify(news_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/digikala", methods=["GET", "POST"])
def digikala():
    """Digikala endpoint"""
    query = request.get_json().get(
        "query") if request.method == "POST" else request.args.get("query")
    page = request.get_json().get(
        "page",
        1) if request.method == "POST" else request.args.get(
        "page",
        1)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    url = f"https://api.digikala.com/v1/search/?q={query}&page={page}"
    return jsonify(requests.get(url).json())


@app.route("/basalam", methods=["GET", "POST"])
def basalam():
    """Basalam endpoint"""
    query = request.get_json().get(
        "query") if request.method == "POST" else request.args.get("query")
    page = request.get_json().get(
        "page",
        1) if request.method == "POST" else request.args.get(
        "page",
        1)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    from_item = (int(page) - 1) * 12
    url = f"https://search.basalam.com/ai-engine/api/v2.0/product/search?from={from_item}&q=query&dynamicFacets=true&size=12&enableNavigations=true&adsImpressionDisable=false&grouped=true"
    return jsonify(requests.get(url).json())


@app.route("/quransearch", methods=["GET", "POST"])
def quransearch():
    """Quran search endpoint"""
    query = request.get_json().get(
        "query") if request.method == "POST" else request.args.get("query")
    page = request.get_json().get(
        "page",
        1) if request.method == "POST" else request.args.get(
        "page",
        1)

    if not query:
        return jsonify({"error": "No query provided"}), 400

    url = f"https://quran.com/api/proxy/search/v1/search?mode=quick&query={query}&get_text=1&highlight=1&per_page=10&page={page}&translation_ids=131"
    return jsonify(requests.get(url).json())


@app.route("/prices", methods=["GET", "POST"])
def prices():
    """Prices endpoint"""
    url = "https://api.dastyar.io/express/financial-item"
    return jsonify(requests.get(url).json())


@app.route("/get_favicon_url", methods=["GET"])
def get_favicon_url(site_url):
    try:
        res = requests.get(site_url, timeout=5)
        soup = bs4.BeautifulSoup(res.text, 'html.parser')

        icon_link = soup.find("link", rel=lambda x: x and 'icon' in x.lower())
        if icon_link and icon_link.get("href"):
            icon_href = icon_link["href"]
            parsed_url = urlparse(site_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            if icon_href.startswith("http"):
                return icon_href
            elif icon_href.startswith("//"):
                return parsed_url.scheme + ":" + icon_href
            elif icon_href.startswith("/"):
                return base_url + icon_href
            else:
                return base_url + "/" + icon_href
        else:
            parsed_url = urlparse(site_url)
            default_favicon = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
            try:
                icon_response = requests.get(default_favicon, timeout=5)
                if icon_response.status_code != 200:
                    domain_first_letter = parsed_url.netloc[0].upper()
                    fallback_icon = f"https://dummyimage.com/128x128/012/666.png&text={domain_first_letter}"
                    return fallback_icon
                return default_favicon
            except BaseException:
                domain_first_letter = parsed_url.netloc[0].upper()
                fallback_icon = f"https://dummyimage.com/128x128/012/666.png&text={domain_first_letter}"
                return fallback_icon
    except Exception as e:
        parsed_url = urlparse(site_url)
        domain_first_letter = parsed_url.netloc[0].upper()
        fallback_icon = f"https://dummyimage.com/128x128/012/666.png&text={domain_first_letter}"
        return fallback_icon


@app.route("/favsite/<path:site_url>")
def get_faviconsite(site_url):
    site_url = site_url if site_url.startswith(
        "http") else "https://" + site_url
    favicon_url = get_favicon_url(site_url)
    if not favicon_url:
        return "Favicon not found", 404

    try:
        icon_response = requests.get(favicon_url, timeout=5)
        if icon_response.status_code == 200 and 'image' in icon_response.headers[
                'Content-Type']:
            return Response(icon_response.content,
                            content_type=icon_response.headers['Content-Type'])
        else:
            return "Favicon no an image", 400
    except Exception as e:
        return "Error retrieving favicon", 500


@app.route("/bale_number_id")
def bale_number_id():
    if request.method == "GET":
        number = request.args.get("number")
        uidg = request.args.get("id")
    elif request.method == "POST":
        number = request.get_json().get("number")
        uidg = request.get_json().get("id")
    if not number or not uidg:
        return jsonify(
            {"status": "error", "message": "Username and user_id are required"}), 400

    data = get_data_from_id("@" + number)

    if data["status"] == "error":
        return jsonify({"status": "error", "message": "number not found"}), 404

    user_id_from_data = str(data["user_id"])
    username_from_data = data["username"]
    print(user_id_from_data, username_from_data)

    if user_id_from_data == str(uidg) or username_from_data == uidg:
        data["status"] = "success"
        return jsonify(data)
    else:
        return jsonify(
            {"status": "error", "message": "User ID does not match"}), 400


@app.route("/bale_id_data")
def bale_id_data():
    if request.method == "GET":
        username = request.args.get("username")
    elif request.method == "POST":
        username = request.get_json().get("username")
    else:
        return jsonify(
            {"status": "error", "message": "Invalid request method"}), 400
    if not username:
        return jsonify(
            {"status": "error", "message": "Username is required"}), 400

    data = get_data_from_id(username)

    if data["status"] == "error":
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify({
        "status": "success",
        "username": username,
        "avatar": data["avatar"],
        "description": data["description"],
        "name": data["name"],
        "is_bot": data["is_bot"],
        "is_verified": data["is_verified"],
        "is_private": data["is_private"],
        "members": data["members"],
        "last_message": data["last_message"],
        "user_id": data["user_id"],
    })


fa_nums = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']


def to_fa_num(num):
    return ''.join(fa_nums[int(i)] if i.isdigit() else i for i in str(num))


def get_date():
    h = jdatetime.datetime.now().strftime('%H:%M:%S')
    with_fa_nums = to_fa_num(h)
    return f'{with_fa_nums}'


@app.route('/holiday', methods=['GET', 'POST'])
def holiday():
    if request.method == 'POST':
        date = request.get_json().get("date")
    elif request.method == 'GET':
        date = request.args.get("date")

    if not date:
        return jsonify({"status": "error", "message": "Date is required"}), 400
    data = requests.get(holiday_api + date).json()

    data["source"] = "https://holiday.ir"
    return jsonify(data)


def date():
    if "hastiyar" in request.args.keys():
        return to_fa_num(jdatetime.datetime.now().strftime('%Y/%m/%d'))

    return jsonify({"status": "error", "message": "Not found"}), 404


@app.route("/quransurahs", methods=['GET', 'POST'])
def quransurahs():
    with open("quran.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
        return jsonify(data)


@app.route("/quranvoice", methods=['GET', 'POST'])
def quranvoice():
    if request.method == 'POST':
        surah = request.get_json().get("surah")
        ayah = request.get_json().get("ayah")
        reciter = request.get_json().get("reciter", "ghamadi")
    elif request.method == 'GET':
        surah = request.args.get("surah")
        ayah = request.args.get("ayah")
        reciter = request.args.get("reciter", "ghamadi")
    if not surah or not ayah:
        return jsonify(
            {"status": "error", "message": "Surah and ayah are required"}), 400

    try:
        surah = int(surah)
        ayah = int(ayah)
    except ValueError:
        return jsonify(
            {"status": "error", "message": "Surah and ayah must be numbers"}), 400

    if surah < 1 or surah > 114:
        return jsonify(
            {"status": "error", "message": "Surah must be between 1 and 114"}), 400

    if ayah < 1 or ayah > 286:
        return jsonify(
            {"status": "error", "message": "Ayah must be between 1 and 286"}), 400

    reciters = []
    with open("reciters.json", "r", encoding="utf-8") as f:
        reciters = json.loads(f.read()).values()

    if reciter not in reciters:
        return jsonify(
            {"status": "error", "message": "Reciter not found"}), 404

    url = f"https://tanzil.ir/res/audio/{reciter}/{str(surah).zfill(3)}{str(ayah).zfill(3)}.mp3"
    data = requests.get(url)
    if data.status_code == 404:
        return jsonify({"status": "error", "message": "Audio not found"}), 404
    return Response(data.content, mimetype="audio/mpeg")


@app.route("/quranreciters", methods=['GET', 'POST'])
def quranreciters():
    file = "reciters.json"
    with open(file, "r", encoding="utf-8") as f:
        data = json.loads(f.read())
        return jsonify(data)


@app.route("/time", methods=['GET', 'POST'])
def time():
    if "hastiyar" in request.args.keys():
        return get_date()

    if request.method == 'POST':
        epoch = request.get_json().get("epoch")
    elif request.method == 'GET':
        epoch = request.args.get("epoch")
    if not epoch:
        now = jdatetime.datetime.now()
        now_g = datetime.datetime.now()
    else:
        try:
            now = jdatetime.datetime.fromtimestamp(int(epoch))
            now_g = datetime.datetime.fromtimestamp(int(epoch))
        except BaseException:
            return jsonify(
                {"status": "error", "message": "Invalid epoch"}), 400
    holidays = get_holiday(now.strftime("%Y/%m/%d"))
    holidays["source"] = "Holidays are taken from https://holidayapi.ir/"
    date_json = {
        "jalali": {
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "weekday": now.weekday(),
            "weekday_name": now.strftime("%A"),
            "month_name": now.strftime("%B"),
            "year_name": now.strftime("%Y"),
            "day_name": now.strftime("%d"),
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%d/%m/%Y")
        },
        "gregorian": {
            "year": now_g.year,
            "month": now_g.month,
            "day": now_g.day,
            "hour": now_g.hour,
            "minute": now_g.minute,
            "second": now_g.second,
            "weekday": now_g.weekday(),
            "weekday_name": now_g.strftime("%A"),
            "month_name": now_g.strftime("%B"),
            "year_name": now_g.strftime("%Y"),
            "day_name": now_g.strftime("%d"),
            "time": now_g.strftime("%H:%M:%S"),
            "date": now_g.strftime("%d/%m/%Y")
        },
        "holidays": holidays
    }
    return jsonify(date_json)


if __name__ == "__main__":
    app.run('0.0.0.0', 8080)
