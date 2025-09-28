from fastapi import FastAPI, Request, HTTPException, Query, Body, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import io
import random
import bs4
import requests
import qrcode
import socket
import ipaddress
import json
from googlesearch import search
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
import uvicorn
from typing import Optional, Dict, Any, List, Union

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

app = FastAPI(title="API Service", description="Comprehensive API service with multiple endpoints")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

translator_suppoted_langs = ["de", "en", "fa", "tr", "ar", "fr", "nl", "zh"]


# Pydantic models for request validation
class TextRequest(BaseModel):
    text: str


class LangRequest(BaseModel):
    text: str
    lang: str


class CityRequest(BaseModel):
    city: str


class URLRequest(BaseModel):
    url: str


class VideoRequest(BaseModel):
    video: str


class SearchRequest(BaseModel):
    text: str
    mode: Optional[str] = None


class PingRequest(BaseModel):
    host: str


class NameRequest(BaseModel):
    name: str


class NewsRequest(BaseModel):
    source: str
    mode: Optional[str] = "rss"


class QueryRequest(BaseModel):
    query: str
    page: Optional[int] = 1


class QuranVoiceRequest(BaseModel):
    surah: int
    ayah: int
    reciter: Optional[str] = "ghamadi"


class LinkRequest(BaseModel):
    url: str


# Helper functions
def get_faal_hafez():
    api = "https://api-free.ir/api/fal"
    res = requests.get(api).json()
    urlt = res["result"]
    return requests.get(urlt).content


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


def google_search(q):
    return search(q, num_results=10, advanced=True)


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
    req = requests.get(url).text
    if """<p class="__404_title__lxIKL">گفتگوی مورد نظر وجود ندارد.</p>""" in req:
        return {"status": "error", "error": "not found"}
    else:
        soup = bs4.BeautifulSoup(req, "html.parser")
        avatar_class = "Avatar_img___C2_3"
        description_class = "Profile_description__YTAr_"
        name_class = "Profile_name__pQglx"
        json_script_id = "__NEXT_DATA__"
        try:
            avatar = soup.find("img", class_=avatar_class)["src"]
        except:
            avatar = None
        try:
            description = soup.find("div", class_=description_class).text
        except:
            description = None
        try:
            name = soup.find("h1", class_=name_class).text
        except:
            name = None
        try:
            json_script = soup.find("script", id=json_script_id).text
        except:
            json_script = None
        try:
            json_data = json.loads(json_script)
        except:
            json_data = {}
        try:
            is_bot = json_data["props"]["pageProps"]["user"]["isBot"]
        except:
            is_bot = False
        try:
            try:
                is_verified = json_data["props"]["pageProps"]["user"]["isVerified"]
            except:
                is_verified = json_data["props"]["pageProps"]["group"]["isVerified"]
        except:
            is_verified = False
        try:
            is_private = True
            if json_data["props"]["pageProps"]["user"] == None:
                is_private = False
        except:
            is_private = False
        try:
            members = json_data["props"]["pageProps"]["group"]["members"]
        except:
            members = None
        try:
            last_message = json_data["props"]["pageProps"]["messages"][-1]["message"]["documentMessage"]["caption"][
                "text"].replace(
                "&zwnj;", "")
        except:
            try:
                last_message = json_data["props"]["pageProps"]["messages"][-1]["message"]["textMessage"][
                    "text"].replace(
                    "&zwnj;", "")
            except:
                last_message = None
        try:
            user_id = json_data["props"]["pageProps"]["peer"]["id"]
        except:
            user_id = None
        try:
            username = json_data["props"]["pageProps"]["user"]["nick"]
        except:
            username = None
        return {
            "status": "success",
            "avatar": avatar,
            "description": description,
            "name": name,
            "is_bot": is_bot,
            "is_verified": is_verified,
            "is_private": is_private,
            "members": members,
            "last_message": last_message,
            "user_id": user_id,
            "username": username
        }


def extract_filename(headers):
    content_disp = headers.get("Content-Disposition")
    if content_disp and "filename=" in content_disp:
        filename = content_disp.split("filename=")[-1].strip('"')
        return filename
    return None


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


fa_nums = ['۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹']


def to_fa_num(num):
    return ''.join(fa_nums[int(i)] if i.isdigit() else i for i in str(num))


def get_date():
    h = jdatetime.datetime.now().strftime('%H:%M:%S')
    with_fa_nums = to_fa_num(h)
    return f'{with_fa_nums}'


# API endpoints
@app.get("/")
async def home():
    return FileResponse("mainpage.html")


@app.get("/aimagic.jpg")
async def aimagic():
    return FileResponse("static/aimagic.jpg", media_type="image/jpeg")


@app.get('/manifest.json')
async def manifest():
    return FileResponse("static/manifest.json", media_type="application/json")


@app.get('/service-worker.js')
async def service_worker():
    return FileResponse("static/service-worker.js", media_type="text/javascript")


@app.post("/tts")
@app.get("/tts")
async def tts(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    audio = get_audio(text)
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/image")
@app.get("/image")
async def image(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

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
        raise HTTPException(status_code=response.status_code, detail="Failed to generate image")
    return Response(content=response.content, media_type="image/jpeg")


@app.post("/logo")
@app.get("/logo")
async def logo(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

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
        raise HTTPException(status_code=response.status_code, detail="Failed to generate image")
    return Response(content=response.content, media_type="image/jpeg")


@app.post("/ai")
@app.get("/ai")
async def ai(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    api_url = f"https://api.majidapi.ir/gpt/35?q={text}&token={MAJIDAPI_TOKEN}"
    result = requests.get(api_url).json()['result']
    return JSONResponse(content={"text": result})


async def process_openrouter_request(text, model, history=[]):
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
        raise HTTPException(status_code=response.status_code,
                            detail="Failed to process request. Call Support (check website's the footer)")
    result = response.json()
    return JSONResponse(content={"text": result["choices"][0]["message"]["content"]})


@app.post("/deepseek")
@app.get("/deepseek")
async def deepseek(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)
        history = data.get("history", [])
    else:
        history = []

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not history:
        return await process_openrouter_request(text, "deepseek/deepseek-chat-v3-0324:free")
    return await process_openrouter_request(text, "deepseek/deepseek-chat-v3-0324:free", history)


@app.post("/qwen")
@app.get("/qwen")
async def qwen(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)
        history = data.get("history", [])
    else:
        history = []

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not history:
        return await process_openrouter_request(text, "qwen/qwen2.5-vl-72b-instruct:free")
    return await process_openrouter_request(text, "qwen/qwen2.5-vl-72b-instruct:free", history)


@app.post("/llama")
@app.get("/llama")
async def llama(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)
        history = data.get("history", [])
    else:
        history = []

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not history:
        return await process_openrouter_request(text, "meta-llama/llama-4-maverick:free")
    return await process_openrouter_request(text, "meta-llama/llama-4-maverick:free", history)


@app.post("/nemotron")
@app.get("/nemotron")
async def nemotron(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)
        history = data.get("history", [])
    else:
        history = []

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    if not history:
        return await process_openrouter_request(text, "nvidia/llama-3.3-nemotron-super-49b-v1:free")
    return await process_openrouter_request(text, "nvidia/llama-3.3-nemotron-super-49b-v1:free", history)


@app.get("/aqi")
async def aqi():
    url = "https://airnow.tehran.ir"
    ids = 'ContentPlaceHolder1_lblAqi3h'

    session = requests.Session()
    response = session.get(url)
    content = response.text
    soup = bs4.BeautifulSoup(content, 'html.parser')
    try:
        aqi_value = soup.find_all('span', {'id': ids})[0].text
        return JSONResponse(content={"aqi": aqi_value})
    except IndexError:
        raise HTTPException(status_code=404, detail="AQI data not found")


@app.post("/translate")
@app.get("/translate")
async def translate(text: Optional[str] = Query(None), lang: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)
        lang = data.get("lang", lang)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    if not lang:
        raise HTTPException(status_code=400, detail="No language provided")
    if lang not in translator_suppoted_langs:
        raise HTTPException(status_code=400,
                            detail=f"Invalid language; supported langs: {' '.join(translator_suppoted_langs)}")

    result = translate_to_any_lang(text, lang)
    return JSONResponse(content={"text": result})


API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3-turbo"
headers = {"Authorization": f"Bearer {HF_TOKEN}"}


def query(file: bytes) -> dict:
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    data = file
    headers["Content-Type"] = "audio/wav"
    response = requests.post(API_URL, headers=headers, data=data, verify=False)
    s = response.json()
    return s["text"]


@app.post("/speechtotext")
async def speechtotext(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        contents = await file.read()
        text = query(contents)
        return JSONResponse(content={"text": text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get_directurl_data")
@app.get("/get_directurl_data")
async def get_directurl_data(url: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        url = data.get("url", url)

    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")

    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        headers = response.headers

        size = headers.get("Content-Length")
        if size:
            size = int(size)
        else:
            size = None

        return JSONResponse(content={
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/textfont")
@app.get("/textfont")
async def textfont(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    api = f"https://api-free.ir/api/font.php?en="
    req = requests.get(api + text).json()
    font = random.choice(req["result"])
    return JSONResponse(content={"text": font})


@app.post("/weather")
@app.get("/weather")
async def weather(city: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        city = data.get("city", city)

    if not city:
        raise HTTPException(status_code=400, detail="No city provided")

    result = fetch_weather(city)
    return JSONResponse(content={"weather": result})


@app.post("/owghat")
@app.get("/owghat")
async def owghat(city: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        city = data.get("city", city)

    if not city:
        raise HTTPException(status_code=400, detail="No city provided")

    result = get_shari_owghat(city)
    return JSONResponse(content={"owghat": result})


@app.get("/faal")
async def faal():
    faal_content = get_faal_hafez()
    return Response(content=faal_content, media_type='image/jpeg')


@app.post("/joke")
@app.get("/joke")
async def joke(type: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        type = data.get("type", type)

    r = requests.get(f"https://api.majidapi.ir/fun/joke?token={MAJIDAPI_TOKEN}")
    joke_ = r.json()['result']

    if type == 'text':
        return Response(content=joke_)
    return JSONResponse(content={"joke": joke_})


@app.get("/danestani")
async def danestani():
    url = f"https://api.majidapi.ir/fun/danestani?token={MAJIDAPI_TOKEN}"
    return JSONResponse(content={"status": "success", "data": requests.get(url).json().get("result")})


@app.get("/ip")
async def ip(request: Request):
    client_ip = request.headers.get('X-Forwarded-For', request.client.host)
    try:
        hostname = socket.gethostbyaddr(client_ip)[0]
    except BaseException:
        hostname = None

    ip_info = requests.get(f"https://ipwho.is/{client_ip}").json()

    if ip_info.get("success"):
        return JSONResponse(content={
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
        return JSONResponse(content={
            "ip": client_ip,
            "hostname": hostname,
            "is_private": ipaddress.ip_address(client_ip).is_private,
            "version": "IPv4" if "." in client_ip else "IPv6",
            "raw_ip": client_ip
        })


@app.post("/whois")
@app.get("/whois")
async def whois_endpoint(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No domain provided")

    url = "https://rasanika.com/api/w/whois?domain=" + text
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch WHOIS data")
    return JSONResponse(content=response.json())


@app.post("/qrcode")
@app.get("/qrcode")
async def generate_qrcode(text: Optional[str] = Query(None),
                          fill_color: Optional[str] = Query("black"),
                          back_color: Optional[str] = Query("white"),
                          box_size: Optional[int] = Query(10),
                          border: Optional[int] = Query(2),
                          request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

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

    return Response(content=img_io.getvalue(), media_type='image/png')


@app.post("/google")
@app.get("/google")
async def google_search_endpoint(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No search query provided")

    l = []
    s = search(text, num_results=15, advanced=True)
    for x in s:
        l.append(
            {
                "title": x.title,
                "url": x.url,
            }
        )
    return JSONResponse(content=l)


@app.post("/aparat")
@app.get("/aparat")
async def aparat_video(video: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        video = data.get("video", video)

    if not video:
        raise HTTPException(status_code=400, detail="No video hash provided")

    try:
        video_data = get_aparat_vid(video)
        if not video_data:
            raise HTTPException(status_code=404, detail="provided video not found")
        return JSONResponse(content=video_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/aparatsearch-video")
@app.get("/aparatsearch-video")
async def aparat_search(text: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)

    if not text:
        raise HTTPException(status_code=400, detail="No search query provided")

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
        return JSONResponse(content=list_)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/searchsong")
@app.get("/searchsong")
async def search_song(text: Optional[str] = Query(None),
                      mode: Optional[str] = Query("default"),
                      request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        text = data.get("text", text)
        mode = data.get("mode", mode)

    if not text:
        raise HTTPException(status_code=400, detail="No search query provided")

    search_results = google_search(text)
    if not search_results:
        raise HTTPException(status_code=404, detail="No results found")

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
                            return JSONResponse(
                                content={"results": [{"url": source["src"], "source_page": result.url}]})

        except (requests.exceptions.RequestException, AttributeError):
            continue

    if found_sources:
        if mode == "random":
            return JSONResponse(content={"results": [random.choice(found_sources)]})
        elif mode.isdigit():
            num = int(mode)
            return JSONResponse(content={"results": found_sources[:num]})
        return JSONResponse(content={"results": found_sources})
    raise HTTPException(status_code=404, detail="No audio sources found")


@app.post("/ping")
@app.get("/ping")
async def ping_view(host: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        host = data.get("host", host)

    if not host:
        raise HTTPException(status_code=400, detail="No host domain provided")

    domain = host.replace("https://", "").replace("http://", "").split("/")[0]

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
    return JSONResponse(content=data)


@app.post("/nameniko")
@app.get("/nameniko")
async def nameniko(name: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        name = data.get("name", name)

    if not name:
        raise HTTPException(status_code=400, detail="No name provided")

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
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Name not found")


@app.post('/news')
@app.get('/news')
async def news(source: Optional[str] = Query(None),
               mode: Optional[str] = Query("rss"),
               request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        source = data.get("source", source)
        mode = data.get("mode", mode)

    if not source:
        raise HTTPException(status_code=400, detail="No source provided")

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
        raise HTTPException(status_code=400, detail="Invalid source")

    if mode not in ['rss', 'json']:
        raise HTTPException(status_code=400, detail="Invalid mode")

    try:
        response = requests.get(NEWS_SOURCES[source])
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch news")

        if mode == 'rss':
            return Response(content=response.text, media_type='application/xml')

        feed = feedparser.parse(NEWS_SOURCES[source])
        news_list = [{
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary
        } for entry in feed.entries]

        return JSONResponse(content=news_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/digikala")
@app.get("/digikala")
async def digikala(query: Optional[str] = Query(None),
                   page: Optional[int] = Query(1),
                   request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        query = data.get("query", query)
        page = data.get("page", page)

    if not query:
        raise HTTPException(status_code=400, detail="No query provided")

    url = f"https://api.digikala.com/v1/search/?q={query}&page={page}"
    return JSONResponse(content=requests.get(url).json())


@app.post("/basalam")
@app.get("/basalam")
async def basalam(query: Optional[str] = Query(None),
                  page: Optional[int] = Query(1),
                  request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        query = data.get("query", query)
        page = data.get("page", page)

    if not query:
        raise HTTPException(status_code=400, detail="No query provided")

    from_item = (int(page) - 1) * 12
    url = f"https://search.basalam.com/ai-engine/api/v2.0/product/search?from={from_item}&q=query&dynamicFacets=true&size=12&enableNavigations=true&adsImpressionDisable=false&grouped=true"
    return JSONResponse(content=requests.get(url).json())


@app.post("/quransearch")
@app.get("/quransearch")
async def quransearch(query: Optional[str] = Query(None),
                      page: Optional[int] = Query(1),
                      request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        query = data.get("query", query)
        page = data.get("page", page)

    if not query:
        raise HTTPException(status_code=400, detail="No query provided")

    url = f"https://quran.com/api/proxy/search/v1/search?mode=quick&query={query}&get_text=1&highlight=1&per_page=10&page={page}&translation_ids=131"
    return JSONResponse(content=requests.get(url).json())


@app.get("/prices")
async def prices():
    url = "https://api.dastyar.io/express/financial-item"
    return JSONResponse(content=requests.get(url).json())


@app.get("/favsite/{site_url:path}")
async def get_faviconsite(site_url: str):
    site_url = site_url if site_url.startswith("http") else "https://" + site_url
    favicon_url = get_favicon_url(site_url)
    if not favicon_url:
        raise HTTPException(status_code=404, detail="Favicon not found")

    try:
        icon_response = requests.get(favicon_url, timeout=5)
        if icon_response.status_code == 200 and 'image' in icon_response.headers.get('Content-Type', ''):
            return Response(content=icon_response.content, media_type=icon_response.headers['Content-Type'])
        else:
            raise HTTPException(status_code=400, detail="Favicon not an image")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving favicon")


@app.post("/bale_number_id")
@app.get("/bale_number_id")
async def bale_number_id(number: Optional[str] = Query(None),
                         uidg: Optional[str] = Query(None),
                         request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        number = data.get("number", number)
        uidg = data.get("id", uidg)

    if not number or not uidg:
        raise HTTPException(status_code=400, detail="Username and user_id are required")

    data = get_data_from_id("@" + number)

    if data["status"] == "error":
        raise HTTPException(status_code=404, detail="number not found")

    user_id_from_data = str(data["user_id"])
    username_from_data = data["username"]

    if user_id_from_data == str(uidg) or username_from_data == uidg:
        data["status"] = "success"
        return JSONResponse(content=data)
    else:
        raise HTTPException(status_code=400, detail="User ID does not match")


@app.post("/bale_id_data")
@app.get("/bale_id_data")
async def bale_id_data(username: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        username = data.get("username", username)

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    data = get_data_from_id(username)

    if data["status"] == "error":
        raise HTTPException(status_code=404, detail="User not found")

    return JSONResponse(content={
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


@app.post('/holiday')
@app.get('/holiday')
async def holiday(date: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        date = data.get("date", date)

    if not date:
        raise HTTPException(status_code=400, detail="Date is required")

    data = requests.get(holiday_api + date).json()
    data["source"] = "https://holiday.ir"
    return JSONResponse(content=data)


@app.get("/date")
async def date(hastiyar: Optional[str] = Query(None)):
    if hastiyar:
        return to_fa_num(jdatetime.datetime.now().strftime('%Y/%m/%d'))
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/quransurahs")
async def quransurahs():
    with open("quran.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
        return JSONResponse(content=data)


@app.post("/quranvoice")
@app.get("/quranvoice")
async def quranvoice(surah: Optional[int] = Query(None),
                     ayah: Optional[int] = Query(None),
                     reciter: Optional[str] = Query("ghamadi"),
                     request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        surah = data.get("surah", surah)
        ayah = data.get("ayah", ayah)
        reciter = data.get("reciter", reciter)

    if not surah or not ayah:
        raise HTTPException(status_code=400, detail="Surah and ayah are required")

    if surah < 1 or surah > 114:
        raise HTTPException(status_code=400, detail="Surah must be between 1 and 114")

    if ayah < 1 or ayah > 286:
        raise HTTPException(status_code=400, detail="Ayah must be between 1 and 286")

    with open("reciters.json", "r", encoding="utf-8") as f:
        reciters = json.loads(f.read()).values()

    if reciter not in reciters:
        raise HTTPException(status_code=404, detail="Reciter not found")

    url = f"https://tanzil.ir/res/audio/{reciter}/{str(surah).zfill(3)}{str(ayah).zfill(3)}.mp3"
    data = requests.get(url)
    if data.status_code == 404:
        raise HTTPException(status_code=404, detail="Audio not found")
    return Response(content=data.content, media_type="audio/mpeg")


@app.get("/quranreciters")
async def quranreciters():
    with open("reciters.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())
        return JSONResponse(content=data)


@app.post("/time")
@app.get("/time")
async def time(epoch: Optional[str] = Query(None),
               hastiyar: Optional[str] = Query(None),
               request: Request = None):
    if hastiyar:
        return get_date()

    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        epoch = data.get("epoch", epoch)

    if not epoch:
        now = jdatetime.datetime.now()
        now_g = datetime.datetime.now()
    else:
        try:
            now = jdatetime.datetime.fromtimestamp(int(epoch))
            now_g = datetime.datetime.fromtimestamp(int(epoch))
        except BaseException:
            raise HTTPException(status_code=400, detail="Invalid epoch")

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
    return JSONResponse(content=date_json)


@app.post("/linkirani")
@app.get("/linkirani")
async def linkirani(url: Optional[str] = Query(None), request: Request = None):
    if request.method == "POST":
        data = await request.json() if request.headers.get("content-type") == "application/json" else {}
        url = data.get("url", url)

    api = "https://api.linkirani.ir/apiv1/shortlink"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-length": "98",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://linkirani.ir",
        "priority": "u=1, i",
        "referer": "https://linkirani.ir/",
        "sec-ch-ua": '"Chromium";v="139", "Not;A=Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }

    data = {
        "url": url
    }

    req = requests.post(api, headers=headers, json=data)

    if req.status_code == 200:
        return JSONResponse(content=req.json())
    else:
        raise HTTPException(status_code=req.status_code, detail="an error from https://linkirani.ir")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)