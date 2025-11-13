from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH
import requests
import base62
import http.cookiejar
#import datetime
import hashlib
import hmac
import math
#import sys
import subprocess
import re
import os
import time





class TOTP:
    def __init__(self) -> None:
        # dumped directly from the object, after all decryptions
        #self.secret=b"3784327687908747137548544428192122"
        #self.secret = b"5507145853487499592248630329347"
        
        #self.secret=b"1001118111179821231246884693781326442819979236535911364106221310730"
        #self.secret = "meZcB\\tlUFV1D6W2Hy4@9+$QaH5)N8"
        #secret_bytes = self.secret.encode("utf-8")
        #self.secret=b"535049484852574949485254545349505056534949575748555749495256485553545049505353495649"
        
        #self.secret=b"1361015212836455521427415682543621839612044"
        #self.secret=b"20142234366103216424883046382624440284418122"
        self.secret=b"5355525355564950525150494849494949555652485356515049494849495749485457544950535553"
        self.version = 23   
        self.period = 30
        self.digits = 6

    def generate(self, timestamp: int) -> str:
        counter = math.floor(timestamp / 1000 / self.period)
        counter_bytes = counter.to_bytes(8, byteorder="big")

        h = hmac.new(self.secret, counter_bytes, hashlib.sha1)
        hmac_result = h.digest()

        offset = hmac_result[-1] & 0x0F
        binary = (
            (hmac_result[offset] & 0x7F) << 24
            | (hmac_result[offset + 1] & 0xFF) << 16
            | (hmac_result[offset + 2] & 0xFF) << 8
            | (hmac_result[offset + 3] & 0xFF)
        )

        return str(binary % (10**self.digits)).zfill(self.digits)



def get_session():
    session=requests.session()
    cookie_jar = http.cookiejar.MozillaCookieJar('./Spotify/cookies.txt')
    cookie_jar.load()
    spotify_cookies = {cookie.name: cookie.value for cookie in cookie_jar if 'spotify.com' in cookie.domain}
    session.cookies.update(spotify_cookies)
    return session

def get_track_id(url):
    regex=r"track/([^?]+)"
    #regex = r"track/([a-zA-Z0-9]+)"
    match=re.search(regex,url)
    if match:
        track_id=match.group(1)
    return track_id

def get_gid_from_id(track_id):
    gid=hex(base62.decode(track_id, base62.CHARSET_INVERTED))[2:].zfill(32)
    return gid




#dobbiamo aggiornare il bearer ottenendo l'access token
#tipo: ?reason=init&productType=web-player&totp=495645&totpServer=495645&totpVer=5&sTime=1743269292&cTime=1743269291873&buildVer=web-player_2025-03-29_1743239319809_0f1ae41&buildDate=2025-03-29

def get_server_time(session):
    server_time_url="https://open.spotify.com/api/server-time"
    server_time=1e3 * int(session.get(server_time_url).json()["serverTime"])
    return server_time
    #return int(time.time() * 1000)

def get_totp(server_time):
    totpC=TOTP()
    totp=totpC.generate(timestamp=server_time)
    return totp

# A horse gave me these numbers!
#
# 39 45 45 41 44 69 5e 5e 38 3a 45 5d 38 32 4a 5e 45 39 36 43 36 32 3d 3d 40 5e 45 40 45 41 5c 44 36 34 43 36 45 44 5e 32 34 45 3a 40 3f 44 5e 43 46 3f 44 5e 64
#
# And I was informed of a simple character substitution cipher that is a variation of the Caesar cipher.
#
# It rotates each printable ASCII character (from ! to ~) by 47 positions, resulting in a different set of characters for both letters, numbers, and symbols.


#THIS IS NOT WORKING 
def get_access_token(totp,server_time,session):
    #TOFIX
    #token_params={
#
    #    "reason":"init",
    #    "productType":"web-player",
    #    "totp":totp,
    #    "totpServer":totp,
    #    "totpVer":"23",
    #    #"ts": str(server_time),
#
    #}
#
#
    #print("Retrieving access token...")
#
    #token_access_url="https://open.spotify.com/api/token"
    #resp=session.get(token_access_url,params=token_params)
    #print(resp.status_code)
    #print(resp.text)
    #access_token=str(session.get(token_access_url,params=token_params).json()['accessToken'])
    #print(access_token)

    #Since it's not working you have to put your own access_token, it can be easily found by opening your netowrk tab
    #while you open a spotify playlist, search for access token among the requests that your browser made
    access_token="" #insert your access token
    return access_token

def get_gid_metadata(session,access_token,gid):

    session.headers.update(
         {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'accept': 'application/json',
        'Connection': 'keep-alive',
        'accept-language': 'en-US',
        'content-type': 'application/json',
        'origin': 'https://open.spotify.com/',
        'priority': 'u=1, i',
        'referer': 'https://open.spotify.com/',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'spotify-app-version': '1.2.46.25.g7f189073',
        'app-platform': 'WebPlayer',
        'Authorization': f"Bearer {access_token}"
    }
    )


    gid_metadata_url=f"https://spclient.wg.spotify.com/metadata/4/track/{gid}?market=from_token"

    gid_metadata=session.get(gid_metadata_url).json()
    return gid_metadata

def get_metadata(gid_metadata):
    file_name=gid_metadata["album"]["artist"][0]["name"]+"-"+gid_metadata["name"]+"-"+gid_metadata["album"]["name"]
    print("metadata found: ",file_name)
    image_url="https://i.scdn.co/image/"+gid_metadata["album"]["cover_group"]["image"][0]["file_id"]
    album_cover=requests.get(image_url)
    with open ("./Spotify/utils/album_cover.jpg","wb") as file:
        file.write(album_cover.content)
    file_name = re.sub(r'[^\w\s-]', '', file_name)  # Remove non-alphanumeric characters
    file_name = re.sub(r'[-\s]+', '_', file_name)   # Replace spaces and hyphens with underscores
    file_name = file_name.strip('_')  # Remove leading/trailing underscores if any
    return file_name,album_cover,image_url


def get_file_id(gid_metadata):
    print("Retrieving file id...")
    for file in gid_metadata["file"]:
        if file["format"] == "MP4_128":
            file_id_128 = file["file_id"]
            break
    print("file_id found:",file_id_128)
    return file_id_128

def get_pssh(session,file_id_128):
    session.headers.clear()
    seektable_url=f"https://seektables.scdn.co/seektable/{file_id_128}.json"
    seektable_json=session.get(seektable_url).json()
    pssh=seektable_json["pssh"]
    print("PSSH found:",pssh)
    return seektable_json,pssh





def get_decryption_key(session,pssh,access_token):
    print("retrieving content decryption key...")
    pssh=PSSH(pssh)

    license_url="https://gew4-spclient.spotify.com/widevine-license/v1/audio/license"
    license_url="https://gue1-spclient.spotify.com/widevine-license/v1/audio/license"
    cdm = Cdm.from_device(Device.load("./Spotify//device.wvd"))
    session_id=cdm.open()

    challenge=cdm.get_license_challenge(session_id,pssh)




    session.headers.update(
    {

        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'accept': 'application/json',
        'Connection': 'keep-alive',
        'accept-language': 'en-US',
        'content-type': 'application/json',
        'origin': 'https://open.spotify.com/',
        'priority': 'u=1, i',
        'referer': 'https://open.spotify.com/',
        'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'spotify-app-version': '1.2.46.25.g7f189073',
        'app-platform': 'WebPlayer',
        'authorization': f'Bearer {access_token}'

        }

    )


    license=session.post(license_url,data=challenge)
    cdm.parse_license(session_id,license.content)

    for key in cdm.get_keys(session_id):
        if(key.type=="CONTENT"):
            decryption_key=str(f"{key.kid.hex}:{key.key.hex()}")    
    decryption_key=re.search(r":([a-fA-F0-9]+)$", decryption_key).group(1)
    print("decryption key:",decryption_key,len(decryption_key))
    
    return cdm,decryption_key,session_id
    
def get_encrypted_song_url(session,file_id_128):
    chunks_url=f"https://gew4-spclient.spotify.com/storage-resolve/v2/files/audio/interactive/10/{file_id_128}?version=10000000&product=9&platform=39&alt=json"
    cdn_url=session.get(chunks_url).json()
    #con encrypted song non scarichi effettivamente la canzone ma ottieni un json con dei server cdn li scarichi effettivamente la canzone quindi lavora su questo...
    encrypted_song_url=cdn_url["cdnurl"][0]
    return str(encrypted_song_url)


def download_encrypted_song(encrypted_song_url,session,seektable_json):

    offset=seektable_json["offset"]
    segments=seektable_json["segments"]
    session.headers.clear()
    session.headers.update({

        "range": f"bytes=0-{str(int(offset-1))}"


    })
    
    encrypted_song=[]
    encrypted_song.append(session.get(encrypted_song_url).content)

    for i,segment in enumerate(segments):
        end_byte=offset + (int(segment[0]) - 1)
        print("segment 0: ",segment[0])
        print("offset:",offset)
        print("endbyte:",end_byte)
        session.headers.clear()
        session.headers.update({

        "range": f"bytes={str(int(offset))}-{str(end_byte)}"


        })
        encrypted_chunk=session.get(encrypted_song_url)
        print(encrypted_chunk.status_code)
        encrypted_chunk=encrypted_chunk.content
        encrypted_song.append(encrypted_chunk)
        offset=int(end_byte+1)

    with open("./Downloads/Spotify/encrypted.mp4","wb") as file:
        for encrypted_chunk_ in encrypted_song:
            file.write(encrypted_chunk_)

def decrypt(decryption_key,file_name):
    subprocess.run(
        [
            "./Spotify/mp4decrpyt/mp4decrypt.exe",
            "--key",
            f"1:{str(decryption_key)}",
            f"./Downloads/Spotify/encrypted.mp4",
            f"./Downloads/Spotify/{file_name}.mp4",
        ],
        check=True,
        shell=False
        )


def main(url,logger):
    session=get_session()
    track_id=get_track_id(url)
    gid=get_gid_from_id(track_id)
    server_time=get_server_time(session)
    totp=get_totp(server_time)
    access_token=get_access_token(totp,server_time,session)
    gid_metadata=get_gid_metadata(session,access_token,gid)
    file_name,_,_=get_metadata(gid_metadata)
    file_id_128=get_file_id(gid_metadata)
    seektable_json,pssh=get_pssh(session,file_id_128)
    cdm,decryption_key,session_id=get_decryption_key(session,pssh,access_token)
    encrypted_song_url=get_encrypted_song_url(session,file_id_128)
    download_encrypted_song(encrypted_song_url,session,seektable_json)
    decrypt(decryption_key,file_name)
    cdm.close(session_id)
