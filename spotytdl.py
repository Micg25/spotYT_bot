import requests
import yt_dlp
from bs4 import BeautifulSoup
import re
import threading
import json
import Spotify_helper
import subprocess
import os

API_KEY=["",""]

yt_api_lock = threading.Lock()

def sanitize_filename(title):
    title = re.sub(r'[^\w\s\-_.]', '', title)
    title = title.strip().replace(" ", "_")
    title = re.sub(r'[._]+$', '', title)
    return title

def get_url_by_query(query, session):
    endpoint="https://www.googleapis.com/youtube/v3/search"
    for key in API_KEY:
        params={
            "key":key,
            "q":query,
            "part":"snippet",
            "maxResults":1,
            "type": "video"
        }

        resp=session.get(endpoint,params=params)
        if(resp.status_code==200):
            break
        else:
            print(f"{resp.status_code}, API KEY is not working, trying another one")
    if (resp.status_code!=200):
            raise RuntimeError(f"Api key is not working")
    print("YOUTUBE API RESPONSE:",resp.status_code)
    jsonresp=resp.json()

    videoId=jsonresp["items"][0]["id"]["videoId"]
    url=f"https://www.youtube.com/watch?v={videoId}"
    print(videoId)
    print(url)
    return url

def download_single_track(url,title,album_cover=None):
    n_try=0
    while True:
        try:
            ydl_opts = {
                'format': 'm4a/bestaudio/best',
                'outtmpl':title,
                'noplaylist': True,
                'postprocessors': [{ 
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                }
                ]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download(url)
                print(f"{title} downloaded")
                if (error_code==0):
                    if album_cover:
                        audio_file = title+".m4a"
                        output_file = title+"_with_cover.m4a"
                        subprocess.run([
                            "ffmpeg", "-y",
                            "-i", audio_file,
                            "-i", album_cover,
                            "-map", "0", "-map", "1",
                            "-c", "copy",
                            "-disposition:1", "attached_pic",
                            output_file
                        ])
                        os.remove(audio_file)  
                        os.rename(output_file,audio_file)  
                    return
                elif(n_try<5):
                    n_try+=1
                    continue
                elif(n_try>5):
                    return title

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()
            if "sign in to confirm your age" in error_msg or "age restriction" in error_msg:
                print(f"Skipping {title} due to age restriction.")
                return title
            elif n_try < 5:
                print(f"Retry {n_try + 1} for {title}")
                n_try += 1
                continue
            else:
                print(f"Failed to download {title} after retries.")
                return title

def prettifySpotifyHtml(url):
    resp=requests.get(url)
    print(resp.status_code)
    soup=BeautifulSoup(resp.text,"html.parser")
    html=soup.prettify()
    with open("response.txt","w",encoding="utf-8") as file:
        file.write(html)
    return soup

def getQueryFromSpotify(soup):
    songtitle=soup.find("meta",attrs={"property":"og:title"})["content"]
    albumtitle=soup.find("meta",attrs={"property":"og:description"})["content"]
    print(songtitle)
    print(albumtitle)
    query=albumtitle+" "+songtitle
    print(query)
    type=(soup.find("meta",attrs={"property":"og:type"})["content"])
    return query

def getSpotifyAlbumCover(soup, session):
    track_view_div = soup.find("div", {"data-testid": "track-view"})
    if track_view_div:
        entity_image_div = track_view_div.find("div", {"data-testid": "entity-image"})
        if entity_image_div:
            img_tag = entity_image_div.find("img")
            if img_tag and img_tag.has_attr("src"):
                url=img_tag["src"]
                print("URL img:", img_tag["src"])
                img=session.get(url)
                image_name = url.split("/")[-1] + ".jpg"
                with open (image_name,"wb") as file:
                    file.write(img.content)
                return image_name      
    return None

def getAlbumQueryFromSpotify(soup):
    albumtitle=soup.find("meta",attrs={"property":"og:title"})["content"]
    artist=soup.find("meta",attrs={"property":"og:description"})["content"]
    regex=r"·\s*Album(.*)"
    artist=re.sub(regex,"",artist)
    print("artist:",artist)
    print("albumtitle:"+albumtitle)
    query=artist+" "+ albumtitle
    print(query)
    return artist

def getTypeFromSpotify(soup):
    type=(soup.find("meta",attrs={"property":"og:type"})["content"])
    return type

def spotifyUrlSanitizer(url):
    regex=r"[&?]si=.*"
    sanitizedurl=re.sub(regex,"",url)
    return sanitizedurl

def threadingDownload(track, title, session, to_erase, to_erase_lock):   
    url=get_url_by_query(track, session)
    result=download_single_track(url,title)   
    if(result):
        with to_erase_lock:
            to_erase.append(result)

def create_yt_playlist(youtube, title, description="Playlist migrated from Spotify with @spotytdlbot"):
    try:
        body = {
            "snippet": {
                "title": title,
                "description": description
            },
            "status": {
                "privacyStatus": "private" 
            }
        }
        request = youtube.playlists().insert(
            part="snippet,status",
            body=body
        )
        response = request.execute()
        print(f"Playlist created: {response['id']}")
        return response["id"]
    except Exception as e:
        print(f"Error while creating the playlist: {e}")
        return None
    
def add_track_to_yt_playlist(youtube, playlist_id, video_id):
    try:
        with yt_api_lock:
            request = youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id
                        }
                    }
                }
            )
            request.execute()
            print(f"Video {video_id} added to the playlist.")
            return True
    except Exception as e:
        print(f"Error while adding video: {video_id}: {e}")
        return False
        
def threadingAddToPlaylist(track, title, index, results_list, session):
    try:
        url = get_url_by_query(track, session)
        if url:
            video_id = getVideoId(url)
            if video_id:
                results_list[index] = video_id
            else:
                print(f"Unable to find the video: {title}")
        else:
            print(f"Unable to find the video: {title}")
    except Exception as e:
        print(f"Thread error while migrating {title}: {e}")

def getPlaylistId(url):
    regex=r"list=([^&]+)" 
    try:
        id=re.findall(regex,url)
        return id[0]
    except Exception as e:
        print("failing retreiving playlist id",e)
        exit()

def getVideoId(url):
    regex=r"v=([^&]+)" 
    try:
        id=re.findall(regex,url)
        if(id):
            return id[0]
        else:
            raise RuntimeError("Invalid URL")
    except Exception as e:
        raise RuntimeError("Invalid URL, can't find the Video ID")

def getVideoIdsFromYtPlaylist(id, session):
    playlistapiurl="https://www.googleapis.com/youtube/v3/playlistItems"
    for key in API_KEY:
        params={
        "key":key,
        "part":"snippet",
        "playlistId":id,
        "maxResults":50,
        }
        resp=session.get(playlistapiurl,params=params)
        if(resp.status_code==200):
            break
        else:
            print("API KEY is not working, trying another one")
    if (resp.status_code!=200):
        raise RuntimeError(f"Api key is not working")
    print(resp.status_code)
    jsonresp=resp.json()
    with open("response.txt","w",encoding="utf-8") as file:
        json.dump(jsonresp,file, indent=4, ensure_ascii=False)
    video_info=[(id["snippet"]["resourceId"]["videoId"],id["snippet"]["title"]) for id in jsonresp["items"]]
    return video_info

def idToYtUrl(id):
    url="https://www.youtube.com/watch?v="+id
    return url

def getTitleFromVideo(id, session):
    API_ENDPOINT="https://www.googleapis.com/youtube/v3/videos"
    for key in API_KEY:
        params={
        "key":key,
        "part":"snippet",
        "id":id,
        }
        resp=session.get(API_ENDPOINT,params=params)
        if(resp.status_code==200):
            break
        else:
            print("API KEY is not working, trying another one")
    if (resp.status_code!=200):
        raise RuntimeError(f"Api key is not working")
    title=resp.json()
    print(title)    
    title=title["items"][0]["snippet"]["title"]
    return title  

def getSpotPlaylistIdFromUrl(url):
    print(url)
    regex=r"playlist/([^?]+)"
    id=re.findall(regex,url)
    print("PLAYLIST ID",id[0])
    return id[0]

def getPlaylistContent(access_token,id,session):
    url="https://api-partner.spotify.com/pathfinder/v2/query" 
    headers= {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'accept': 'application/json',
        'Connection': 'keep-alive',
        'accept-language': 'en-US',
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
        'Authorization': f'Bearer {access_token}',
        'content-type':'application/json;charset=UTF-8'
    }

    payload={
        "extensions":{"persistedQuery":{
            "sha256Hash": "cd2275433b29f7316176e7b5b5e098ae7744724e1a52d63549c76636b3257749",
            "version":1
        }
        },
        "operationName":"fetchPlaylist", 
        "variables":{   
        'enableWatchFeedEntrypoint': False,
         "uri": f"spotify:playlist:{str(id)}", 
         "offset": 0, 
         "limit": 5000,}


    }

    resp=session.post(url,json=payload,headers=headers)
    print("Playlist fetching:",resp.status_code)
    return resp.json()

def getTitlesFromSpotPlaylist(json):
    titles=[]
    for item in json["data"]["playlistV2"]["content"]["items"]:
        title=""
        for artist in item["itemV2"]["data"]["albumOfTrack"]["artists"]["items"]:
            if(title==""):
                title=artist["profile"]["name"]
                continue
            title=title+" "+artist["profile"]["name"]
        title=title+" "+item["itemV2"]["data"]["name"]
        titles.append(title)    
    return titles

def main(url,cmd=None,youtube_client=None):
    session = requests.Session()
    to_erase = []
    to_erase_lock = threading.Lock()
    try:
        if(cmd is None):
            if(url.startswith("https://open.spotify.com")):
                url=spotifyUrlSanitizer(url) 
                soup=prettifySpotifyHtml(url)   
                type=getTypeFromSpotify(soup)
                if(type=="music.song"):
                    query=getQueryFromSpotify(soup)
                    album_cover_img=getSpotifyAlbumCover(soup, session)
                    url=get_url_by_query(query, session)
                    id=getVideoId(url)
                    title=getTitleFromVideo(id, session)
                    title=sanitize_filename(title)
                    download_single_track(url,title,album_cover_img)
                    return title
                if(type=="music.album"):
                    query=getAlbumQueryFromSpotify(soup)
                    spans=soup.find_all('span',class_=lambda c: c and c.startswith("ListRowTitle") )
                    tracks=[span.get_text() for span in spans]
                    tracks=[(i,query+" "+track) for i,track in enumerate(tracks)]
                    threads = []
                    titles=[]
                    for track in tracks:
                        title=sanitize_filename(track[1])
                        titles.append(title)
                        thread = threading.Thread(target=threadingDownload, args=(track[1], title, session, to_erase, to_erase_lock))
                        threads.append(thread)
                        thread.start()
                    for thread in threads:
                        thread.join()           
                if(type=="music.playlist"):
                    time=Spotify_helper.get_server_time(session)
                    totp=Spotify_helper.get_totp(time)
                    access_token=Spotify_helper.get_access_token(totp,time,session)
                    id=getSpotPlaylistIdFromUrl(url)
                    playlistjson=getPlaylistContent(access_token,id,session)
                    tracks=getTitlesFromSpotPlaylist(playlistjson)
                    threads = []
                    titles=[]
                    for track in tracks:
                        title=sanitize_filename(track)
                        titles.append(title)
                        thread = threading.Thread(target=threadingDownload, args=(track, title, session, to_erase, to_erase_lock))
                        threads.append(thread)
                        thread.start()
                    for thread in threads:
                        thread.join()    
                    print(titles)
                if(to_erase):
                    clean_titles=[t for t in titles if t not in to_erase]
                    return list(clean_titles)
                else:
                    return list(titles)   

            elif(url.startswith("https://www.youtube.com/watch")):
                id=getVideoId(url)
                title=getTitleFromVideo(id, session)
                title=sanitize_filename(title)
                download_single_track(url,title)
                return title
            elif(url.startswith("https://www.youtube.com/playlist")):
                id=getPlaylistId(url)
                video_info=getVideoIdsFromYtPlaylist(id, session)
                video_info= [ (idToYtUrl(v_id), title) for v_id, title in video_info]
                print(video_info)
                titles=[]
                threads=[]
                for vurl,title in video_info:
                    title=sanitize_filename(title)
                    titles.append(title)
                    thread = threading.Thread(target=download_single_track, args=(vurl,title))
                    threads.append(thread)
                    thread.start()
                for thread in threads:
                    thread.join()
                if(to_erase):
                    clean_titles=[t for t in titles if t not in to_erase]
                    return list(clean_titles)
                else:
                    return list(titles)
            else:
                raise RuntimeError("Invalid URL")
        else:
            if not youtube_client:
                raise RuntimeError("Missing Youtube Client")
            
            time=Spotify_helper.get_server_time(session)
            totp=Spotify_helper.get_totp(time)
            access_token=Spotify_helper.get_access_token(totp,time,session)
            id=getSpotPlaylistIdFromUrl(url)    
            playlistjson=getPlaylistContent(access_token,id,session)
            tracks=getTitlesFromSpotPlaylist(playlistjson)
            try:
                playlist_name = playlistjson["data"]["playlistV2"]["name"]
            except:
                playlist_name = "Playlist Migrated with @SpotYT"

            yt_playlist_id = create_yt_playlist(youtube_client, playlist_name)
            
            if not yt_playlist_id:
                raise RuntimeError("Unable to create a Youtube playlist")
            
            titles = []
            threads = []
            
            ordered_video_ids = [None] * len(tracks)

            for i, track in enumerate(tracks):
                title = sanitize_filename(track)
                titles.append(title)
                
                thread = threading.Thread(target=threadingAddToPlaylist, args=(track, title, i, ordered_video_ids, session))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()    
            
            print("Adding to the playlist...")

            for video_id in ordered_video_ids:
                if video_id:
                    add_track_to_yt_playlist(youtube_client, yt_playlist_id, video_id)
            
            print("Migration completed", titles)
            return titles

    except RuntimeError as e:
        raise RuntimeError(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main("")