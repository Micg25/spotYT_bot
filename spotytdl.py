import requests
import yt_dlp
from bs4 import BeautifulSoup
import re
import threading
import json
import Spotify_helper
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor

# Custom exception for YouTube API quota exceeded
class QuotaExceededException(Exception):
    pass

API_KEY=[""]
SOCS="" # Your Youtube SOCS cookie value here

def sanitize_filename(title):
    title = re.sub(r'[^\w\s\-_.]', '', title)
    title = title.strip().replace(" ", "_")
    title = re.sub(r'[._]+$', '', title)
    return title

def get_url_by_query(query, session):
    # Use YouTube's public endpoint instead of API keys
    endpoint = "https://www.youtube.com/results"
    # Replace spaces with "+" for the query
    formatted_query = query.replace(" ", "+")
    params = {
        "search_query": formatted_query
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    cookies = {
       
        'SOCS': SOCS
    }
    
    resp = session.get(endpoint, params=params, headers=headers, cookies=cookies)
    
    if resp.status_code != 200:
        print(f"YouTube search failed with status code: {resp.status_code} for query: {query}")
        return None
    
    print("YOUTUBE SEARCH RESPONSE:", resp.status_code)
    
    # Search for the videoId in the HTML page content
    # YouTube includes video data in a JSON object within the page
    video_id_match = re.search(r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', resp.text)
    
    if not video_id_match:
        print(f"Unable to find video for query: {query}")
        return None
    
    videoId = video_id_match.group(1)
    url = f"https://www.youtube.com/watch?v={videoId}"
    print(videoId)
    print(url)
    return url

def download_single_track(url,title,album_cover=None,chat_id=None):
    if chat_id:
        filename = title + str(chat_id)
    else:
        filename = title
    n_try=0
    while True:
        try:
            ydl_opts = {
                'format': 'm4a/bestaudio/best',
                'outtmpl':filename,
                'noplaylist': True,
                'postprocessors': [{ 
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                }
                ]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download(url)
                print(f"{filename} downloaded")
                if (error_code==0):
                    if album_cover:
                        audio_file = filename+".m4a"
                        output_file = filename+"_with_cover.m4a"
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

def threadingDownload(track, title, session, to_erase, to_erase_lock, chat_id):   
    url=get_url_by_query(track, session)
    if not url:
        print(f"Skipping {title} - unable to find on YouTube")
        with to_erase_lock:
            to_erase.append(title)
        return
    result=download_single_track(url,title,chat_id=chat_id)   
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
                "privacyStatus": "unlisted" 
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
        error_str = str(e)
        if "quotaExceeded" in error_str or "quota" in error_str.lower():
            print(f"Quota exceeded while creating playlist: {e}")
            raise QuotaExceededException("YouTube API quota exceeded")
        print(f"Error while creating the playlist: {e}")
        return None

def create_spotify_playlist(spotify_client, name, description="Playlist migrated from YouTube with @spotytdlbot"):
    try:
        user_id = spotify_client.current_user()["id"]
        playlist = spotify_client.user_playlist_create(
            user=user_id,
            name=name,
            public=True,
            description=description
        )
        print(f"Spotify playlist created: {playlist['id']}")
        return playlist["id"]
    except Exception as e:
        print(f"Error while creating Spotify playlist: {e}")
        return None

def search_spotify_track(spotify_client, query):
    try:
        results = spotify_client.search(q=query, type="track", limit=1)
        if results["tracks"]["items"]:
            track = results["tracks"]["items"][0]
            track_uri = track["uri"]
            track_name = track["name"]
            print(f"Found on Spotify: {track_name}")
            return track_uri
        else:
            print(f"No results on Spotify for: {query}")
            return None
    except Exception as e:
        print(f"Error searching on Spotify for '{query}': {e}")
        return None

def add_track_to_spotify_playlist(spotify_client, playlist_id, track_uri):
    try:
        spotify_client.playlist_add_items(playlist_id, [track_uri])
        print(f"Track {track_uri} added to Spotify playlist")
        return True
    except Exception as e:
        print(f"Error adding track to Spotify playlist: {e}")
        return False

def get_spotify_playlist_tracks(spotify_client, playlist_id):
    """Gets all track URIs already present in a Spotify playlist"""
    try:
        track_uris = []
        offset = 0
        limit = 100
        
        while True:
            results = spotify_client.playlist_tracks(playlist_id, offset=offset, limit=limit)
            items = results['items']
            
            for item in items:
                if item['track'] and item['track']['uri']:
                    track_uris.append(item['track']['uri'])
            
            if len(items) < limit:
                break
            offset += limit
        
        print(f"Found {len(track_uris)} existing tracks in Spotify playlist")
        return track_uris
    except Exception as e:
        print(f"Error getting Spotify playlist tracks: {e}")
        return []
    
def add_track_to_yt_playlist(youtube, playlist_id, video_id, yt_api_lock):
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
        error_str = str(e)
        # Check if it's a quota error
        if "quotaExceeded" in error_str or ("quota" in error_str.lower() and "403" in error_str):
            print(f"Quota exceeded while adding video {video_id}: {e}")
            raise QuotaExceededException("YouTube API quota exceeded")
        # YouTube API returns an error if the video is already in the playlist
        if "videoAlreadyInPlaylist" in error_str or "duplicate" in error_str.lower():
            print(f"Video {video_id} already in playlist, skipping.")
            return True  # Consider it as a success anyway
        else:
            print(f"Error while adding video: {video_id}: {e}")
            return False
        
def threadingAddToPlaylist(track, title, index, results_list, session, existing_video_ids=None):
    try:
        url = get_url_by_query(track, session)
        if url:
            video_id = getVideoId(url)
            if video_id:
                # If existing_video_ids is provided and the video is already present, skip
                if existing_video_ids and video_id in existing_video_ids:
                    print(f"Video {video_id} already in playlist, skipping.")
                    return
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

def getAllVideoIdsFromPlaylist(yt_playlist_id, session):
    # Use YouTube's public endpoint instead of API keys
    print(f"Fetching all video IDs from playlist: {yt_playlist_id}")
    playlist_url = f"https://www.youtube.com/playlist?list={yt_playlist_id}"
    
    headers = {
        'Device-Memory': '8',
        'Sec-Ch-Dpr': '1.1',
        'sec-ch-ua':'"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-form-factors': '"Desktop"',
        'sec-ch-ua-full-version': '"143.0.7499.193"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="143.0.7499.193", "Chromium";v="143.0.7499.193", "Not A(Brand";v="24.0.0.0"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'https://www.youtube.com/',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    cookies = {
        'SOCS': SOCS
    }
    
    video_ids = set()
    
    # First request to get the playlist page
    resp = session.get(playlist_url, headers=headers, cookies=cookies)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch playlist: {resp.status_code}")
    
    #print(resp.text)
    html_content = resp.text
    print("Initial playlist response:", resp.status_code)
    with open("playlist_page.html","w",encoding="utf-8") as file:
        file.write(html_content)

    # Extract INNERTUBE_API_KEY from the page
    api_key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html_content)
    if not api_key_match:
        raise RuntimeError("Unable to find INNERTUBE_API_KEY")
    innertube_api_key = api_key_match.group(1)
    
    # Extract only videoIds that are inside playlistVideoRenderer to avoid suggested/sidebar videos
    # Pattern that searches for playlistVideoRenderer followed by videoId
    renderer_pattern = r'"playlistVideoRenderer":\s*\{[^}]*"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"'
    video_id_matches = re.findall(renderer_pattern, html_content)
    for vid in video_id_matches:
        video_ids.add(vid)
    
    print(f"Found {len(video_ids)} video IDs in first page")
    
    # Search for continuation token for pagination - more flexible pattern
    continuation_match = re.search(r'"token"\s*:\s*"([^"]+)"[^}]*"request"\s*:\s*"CONTINUATION_REQUEST_TYPE_BROWSE"', html_content)
    if not continuation_match:
        continuation_match = re.search(r'"continuationCommand"\s*:\s*\{[^}]*"token"\s*:\s*"([^"]+)"', html_content)
    
    # Loop per ottenere tutte le pagine
    while continuation_match:
        continuation_token = continuation_match.group(1)
        print(f"Fetching continuation...")
        
        # Richiesta POST per ottenere più video
        browse_url = f"https://www.youtube.com/youtubei/v1/browse?key={innertube_api_key}"
        
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00"
                }
            },
            "continuation": continuation_token
        }
        
        browse_resp = session.post(browse_url, json=payload, headers=headers, cookies=cookies)
        if browse_resp.status_code != 200:
            print(f"Failed to fetch continuation: {browse_resp.status_code}")
            break
        
        browse_content = browse_resp.text
        with open("continuation_page.html","w",encoding="utf-8") as file:
            file.write(browse_content)
        # Extract only videoIds that are inside playlistVideoRenderer
        new_video_ids = re.findall(renderer_pattern, browse_content)
        print(f"Found {len(new_video_ids)} video IDs in continuation")
        for vid in new_video_ids:
            video_ids.add(vid)

        # Search for the next continuation token
        continuation_match = re.search(r'"token"\s*:\s*"([^"]+)"[^}]*"request"\s*:\s*"CONTINUATION_REQUEST_TYPE_BROWSE"', browse_content)
        if not continuation_match:
            continuation_match = re.search(r'"continuationCommand"\s*:\s*\{[^}]*"token"\s*:\s*"([^"]+)"', browse_content)
    
    print(f"Total video IDs retrieved: {len(video_ids)}")
    return video_ids

def getVideoIdsFromYtPlaylist(id, session):
    # Use the same web scraping approach as getAllVideoIdsFromPlaylist
    print(f"Fetching video IDs and titles from playlist: {id}")
    playlist_url = f"https://www.youtube.com/playlist?list={id}"
    
    headers = {
        'Device-Memory': '8',
        'Sec-Ch-Dpr': '1.1',
        'sec-ch-ua':'"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-form-factors': '"Desktop"',
        'sec-ch-ua-full-version': '"143.0.7499.193"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="143.0.7499.193", "Chromium";v="143.0.7499.193", "Not A(Brand";v="24.0.0.0"',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': 'https://www.youtube.com/',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    cookies = {
        'SOCS': SOCS
    }
    
    video_info_list = []
    
    # First request to get the playlist page
    resp = session.get(playlist_url, headers=headers, cookies=cookies)
    with open("playlist_page.html","w",encoding="utf-8") as file:
        file.write(resp.text)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch playlist: {resp.status_code}")
    
    html_content = resp.text
    print("Initial playlist response:", resp.status_code)
    
    # Extract INNERTUBE_API_KEY from the page
    api_key_match = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html_content)
    if not api_key_match:
        raise RuntimeError("Unable to find INNERTUBE_API_KEY")
    innertube_api_key = api_key_match.group(1)
    
    # Pattern that searches for playlistVideoRenderer -> videoId -> thumbnail -> title
    # This ensures the title is inside playlistVideoRenderer and after thumbnail
    renderer_pattern = r'"playlistVideoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})".*?"thumbnail".*?"title":\{"runs":\[\{"text":"([^"]+)"'
    matches = re.findall(renderer_pattern, html_content, re.DOTALL)
    
    for video_id, title in matches:
        video_info_list.append((video_id, title))
    
    print(f"Found {len(video_info_list)} videos with titles in first page")
    
    # Search for continuation token for pagination
    continuation_match = re.search(r'"token"\s*:\s*"([^"]+)"[^}]*"request"\s*:\s*"CONTINUATION_REQUEST_TYPE_BROWSE"', html_content)
    if not continuation_match:
        continuation_match = re.search(r'"continuationCommand"\s*:\s*\{[^}]*"token"\s*:\s*"([^"]+)"', html_content)
    
    # Loop per ottenere tutte le pagine
    while continuation_match:
        continuation_token = continuation_match.group(1)
        print(f"Fetching continuation...")
        
        # Richiesta POST per ottenere più video
        browse_url = f"https://www.youtube.com/youtubei/v1/browse?key={innertube_api_key}"
        
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00"
                }
            },
            "continuation": continuation_token
        }
        
        browse_resp = session.post(browse_url, json=payload, headers=headers, cookies=cookies)
        if browse_resp.status_code != 200:
            print(f"Failed to fetch continuation: {browse_resp.status_code}")
            break
        
        browse_content = browse_resp.text
        
        # Extract videoId and title from continuation response using the same pattern
        new_matches = re.findall(renderer_pattern, browse_content, re.DOTALL)
        print(f"Found {len(new_matches)} videos with titles in continuation")
        for video_id, title in new_matches:
            video_info_list.append((video_id, title))

        # Search for the next continuation token
        continuation_match = re.search(r'"token"\s*:\s*"([^"]+)"[^}]*"request"\s*:\s*"CONTINUATION_REQUEST_TYPE_BROWSE"', browse_content)
        if not continuation_match:
            continuation_match = re.search(r'"continuationCommand"\s*:\s*\{[^}]*"token"\s*:\s*"([^"]+)"', browse_content)
    
    print(f"Total videos retrieved with titles: {len(video_info_list)}")
    return video_info_list

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
    offset=0
    limit=1000  # Reduced from 5000 to 1000 to avoid timeouts
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
         "offset": offset, 
         "limit": limit,}
    }

    # Retry logic to handle timeouts
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            resp=session.post(url,json=payload,headers=headers,timeout=30)
            print("Playlist fetching:",resp.status_code)
            
            if resp.status_code == 504:
                retry_count += 1
                print(f"Timeout (504), retry {retry_count}/{max_retries}...")
                import time
                time.sleep(2)
                continue
            
            if resp.status_code != 200:
                print(f"Error: Received status code {resp.status_code}")
                print(f"Response text: {resp.text[:500]}")
                raise RuntimeError(f"Failed to fetch playlist: {resp.status_code}")
            
            break
        except requests.exceptions.Timeout:
            retry_count += 1
            print(f"Request timeout, retry {retry_count}/{max_retries}...")
            import time
            time.sleep(2)
            if retry_count >= max_retries:
                raise RuntimeError("Failed to fetch playlist after multiple retries")
    
    try:
        first_response = resp.json()
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(f"Response text: {resp.text[:500]}")
        raise RuntimeError(f"Invalid JSON response from Spotify API")
    
    total = first_response["data"]["playlistV2"]["content"]["totalCount"]
    print(f"Total tracks in playlist: {total}")
    
    # Save all items from the first request
    all_items = first_response["data"]["playlistV2"]["content"]["items"]
    
    # Fetch subsequent pages
    if total > limit:
        print(f"Playlist has more than {limit} tracks, fetching all pages...")
        while offset + limit < total:
            offset += limit
            payload["variables"]["offset"] = offset
            
            # Retry logic for each page
            retry_count = 0
            while retry_count < max_retries:
                try:
                    resp = session.post(url, json=payload, headers=headers, timeout=30)
                    
                    if resp.status_code == 504:
                        retry_count += 1
                        print(f"Timeout on page, retry {retry_count}/{max_retries}...")
                        import time
                        time.sleep(2)
                        continue
                    
                    if resp.status_code == 200:
                        next_page = resp.json()
                        next_items = next_page["data"]["playlistV2"]["content"]["items"]
                        all_items.extend(next_items)
                        print(f"Fetched {len(all_items)}/{total} tracks")
                        break
                    else:
                        print(f"Error fetching page at offset {offset}: {resp.status_code}")
                        break
                except requests.exceptions.Timeout:
                    retry_count += 1
                    print(f"Page request timeout, retry {retry_count}/{max_retries}...")
                    import time
                    time.sleep(2)
                    if retry_count >= max_retries:
                        print(f"Skipping page at offset {offset} after timeout")
                        break
            
            # Small delay between requests to avoid rate limiting
            import time
            time.sleep(0.5)
        
        # Update the final JSON with all combined items
        first_response["data"]["playlistV2"]["content"]["items"] = all_items
    
    with open("spot_playlist_response.json","w",encoding="utf-8") as file:
        json.dump(first_response, file, indent=4, ensure_ascii=False)
    
    return first_response

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

def main(url,yt_pl_id=None,cmd=None,youtube_client=None,spotify_client=None,chat_id=None):
    session = requests.Session()
    to_erase = []
    to_erase_lock = threading.Lock()
    yt_api_lock = threading.Lock()
    
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
                    download_single_track(url,title,album_cover_img,chat_id=chat_id)
                    return title
                if(type=="music.album"):
                    query=getAlbumQueryFromSpotify(soup)
                    spans=soup.find_all('span',class_=lambda c: c and c.startswith("ListRowTitle") )
                    tracks=[span.get_text() for span in spans]
                    tracks=[(i,query+" "+track) for i,track in enumerate(tracks)]
                    titles=[]
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        futures = []
                        for track in tracks:
                            title=sanitize_filename(track[1])
                            titles.append(title)
                            futures.append(executor.submit(threadingDownload, track[1], title, session, to_erase, to_erase_lock, chat_id))
                        for future in futures:
                            future.result()          
                if(type=="music.playlist"):
                    time=Spotify_helper.get_server_time(session)
                    totp=Spotify_helper.get_totp(time)
                    access_token=Spotify_helper.get_access_token(totp,time,session)
                    id=getSpotPlaylistIdFromUrl(url)
                    playlistjson=getPlaylistContent(access_token,id,session)
                    tracks=getTitlesFromSpotPlaylist(playlistjson)
                    titles=[]
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        futures = []
                        for track in tracks:
                            title=sanitize_filename(track)
                            titles.append(title)
                            futures.append(executor.submit(threadingDownload, track, title, session, to_erase, to_erase_lock, chat_id))
                        for future in futures:
                            future.result()    
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
                download_single_track(url,title,chat_id=chat_id)
                return title
            elif(url.startswith("https://www.youtube.com/playlist")):
                id=getPlaylistId(url)
                video_info=getVideoIdsFromYtPlaylist(id, session)
                video_info= [ (idToYtUrl(v_id), title) for v_id, title in video_info]
                print(video_info)
                titles=[]
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = []
                    for vurl,title in video_info:
                        title=sanitize_filename(title)
                        titles.append(title)
                        futures.append(executor.submit(download_single_track, vurl, title, None, chat_id))
                    for future in futures:
                        future.result()
                if(to_erase):
                    clean_titles=[t for t in titles if t not in to_erase]
                    return list(clean_titles)
                else:
                    return list(titles)
            else:
                raise RuntimeError("Invalid URL")
        elif(cmd=="migrate_playlist"):
            if not youtube_client:
                raise RuntimeError("Missing Youtube Client")
            
            time=Spotify_helper.get_server_time(session)
            totp=Spotify_helper.get_totp(time)
            access_token=Spotify_helper.get_access_token(totp,time,session)
            id=getSpotPlaylistIdFromUrl(url)    
            playlistjson=getPlaylistContent(access_token,id,session)
            all_tracks=getTitlesFromSpotPlaylist(playlistjson)
            
            # Limit to maximum 200 tracks
            tracks = all_tracks[:200]
            if len(all_tracks) > 200:
                print(f"Playlist has {len(all_tracks)} tracks, processing only first 200")
            
            try:
                playlist_name = playlistjson["data"]["playlistV2"]["name"]
            except:
                playlist_name = "Playlist Migrated with @spotytdlbot"

            yt_playlist_id = create_yt_playlist(youtube_client, playlist_name)
            
            if not yt_playlist_id:
                raise RuntimeError("Unable to create a Youtube playlist")
            
            titles = []
            ordered_video_ids = [None] * len(tracks)

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for i, track in enumerate(tracks):
                    title = sanitize_filename(track)
                    titles.append(title)
                    futures.append(executor.submit(threadingAddToPlaylist, track, title, i, ordered_video_ids, session))
                for future in futures:
                    future.result()
            
            print("Adding to the playlist...")

            for video_id in ordered_video_ids:
                if video_id:
                    add_track_to_yt_playlist(youtube_client, yt_playlist_id, video_id, yt_api_lock)
            
            print("Migration completed", titles)
            return titles
        elif(cmd=="addtoplaylist"):
            print("Adding to existing playlist...")
            if not youtube_client:
                raise RuntimeError("Missing Youtube Client")
            
            time=Spotify_helper.get_server_time(session)
            totp=Spotify_helper.get_totp(time)
            access_token=Spotify_helper.get_access_token(totp,time,session)
            id=getSpotPlaylistIdFromUrl(url)    
            playlistjson=getPlaylistContent(access_token,id,session)
            tracks=getTitlesFromSpotPlaylist(playlistjson)
            yt_playlist_id=getPlaylistId(yt_pl_id)
            if not yt_playlist_id:
                raise RuntimeError("Unable to find the Youtube playlist")
            
            # Get all video IDs already present in the playlist
            print("Fetching existing videos from YouTube playlist...")
            existing_video_ids = getAllVideoIdsFromPlaylist(yt_playlist_id, session)
            print(f"Found {len(existing_video_ids)} existing videos in the playlist")
            
            # Process only tracks after those already present
            start_index = len(existing_video_ids)
            if start_index >= len(tracks):
                print(f"All {len(tracks)} tracks are already in the playlist. Nothing to add.")
                return []
            
            print(f"Skipping first {start_index} tracks (already in playlist)")
            print(f"Processing tracks from {start_index + 1} to {len(tracks)}")
            
            titles = []
            ordered_video_ids = [None] * len(tracks)

            # Limit to maximum 199 tracks per batch
            end_index = min(start_index + 199, len(tracks))
            print(f"Processing batch: tracks {start_index + 1} to {end_index} (max 199 per batch)")

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for i in range(start_index, end_index):
                    track = tracks[i]
                    title = sanitize_filename(track)
                    titles.append(title)
                    futures.append(executor.submit(threadingAddToPlaylist, track, title, i, ordered_video_ids, session, existing_video_ids))
                for future in futures:
                    future.result()
            
            print("Adding new videos to the playlist...")
            
            added_count = 0
            
            for video_id in ordered_video_ids:
                if video_id:
                    add_track_to_yt_playlist(youtube_client, yt_playlist_id, video_id, yt_api_lock)
                    added_count += 1
            
            print(f"✅ Added {added_count} new videos")
            
            print("Migration completed", titles)
            return titles
        elif(cmd=="migrate_yt_to_spotify"):
            print("Migrating YouTube playlist to Spotify...")
            if not spotify_client:
                raise RuntimeError("Missing Spotify Client - you must login to Spotify first")
            
            # Estrai ID playlist YouTube
            yt_playlist_id = getPlaylistId(url)
            if not yt_playlist_id:
                raise RuntimeError("Unable to find YouTube playlist ID")
            
            # Get all videos with titles from YouTube playlist
            print("Fetching videos from YouTube playlist...")
            video_info_list = getVideoIdsFromYtPlaylist(yt_playlist_id, session)
            
            if not video_info_list:
                raise RuntimeError("YouTube playlist is empty or not accessible")
            
            # Limit to 200 tracks
            if len(video_info_list) > 200:
                print(f"Playlist has {len(video_info_list)} videos, processing only first 200")
                video_info_list = video_info_list[:200]
            
            # Extract playlist name from first request (using the same method)
            # For now use a generic name, we can improve later
            playlist_name = f"YouTube Playlist {yt_playlist_id[:8]} - Migrated"
            
            # Create Spotify playlist
            spotify_playlist_id = create_spotify_playlist(spotify_client, playlist_name)
            if not spotify_playlist_id:
                raise RuntimeError("Unable to create Spotify playlist")
            
            # For each video, search on Spotify and add to playlist
            titles = []
            added_count = 0
            skipped_count = 0
            
            for video_id, video_title in video_info_list:
                print(f"Processing: {video_title}")
                titles.append(video_title)
                
                # Search for the track on Spotify
                track_uri = search_spotify_track(spotify_client, video_title)
                
                if track_uri:
                    # Add to Spotify playlist
                    success = add_track_to_spotify_playlist(spotify_client, spotify_playlist_id, track_uri)
                    if success:
                        added_count += 1
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
                    print(f"⚠️ Skipped: {video_title} (not found on Spotify)")
            
            print(f"✅ Migration completed: {added_count} tracks added, {skipped_count} skipped")
            return titles
        elif(cmd=="add_yt_to_spotify_playlist"):
            print("Adding YouTube playlist tracks to existing Spotify playlist...")
            if not spotify_client:
                raise RuntimeError("Missing Spotify Client - you must login to Spotify first")
            
            # Extract YouTube playlist ID
            yt_playlist_id = getPlaylistId(url)
            if not yt_playlist_id:
                raise RuntimeError("Unable to find YouTube playlist ID")
            
            # Extract Spotify playlist ID from second argument
            # yt_pl_id contains the Spotify playlist URL in this case
            spotify_playlist_url = yt_pl_id
            # Extract ID from Spotify URL
            spotify_id_match = re.search(r'playlist/([a-zA-Z0-9]+)', spotify_playlist_url)
            if not spotify_id_match:
                raise RuntimeError("Unable to find Spotify playlist ID")
            spotify_playlist_id = spotify_id_match.group(1)
            
            # Get all tracks already present in Spotify playlist
            print("Fetching existing tracks from Spotify playlist...")
            existing_track_uris = get_spotify_playlist_tracks(spotify_client, spotify_playlist_id)
            start_index = len(existing_track_uris)
            
            # Get all videos with titles from YouTube playlist
            print("Fetching videos from YouTube playlist...")
            video_info_list = getVideoIdsFromYtPlaylist(yt_playlist_id, session)
            
            if not video_info_list:
                raise RuntimeError("YouTube playlist is empty or not accessible")
            
            # Check if there are new tracks to add
            if start_index >= len(video_info_list):
                print(f"All {len(video_info_list)} tracks are already in the Spotify playlist. Nothing to add.")
                return []
            
            print(f"Skipping first {start_index} tracks (already in playlist)")
            print(f"Processing tracks from {start_index + 1} to {len(video_info_list)}")
            
            # Limit to maximum 199 tracks per batch
            end_index = min(start_index + 199, len(video_info_list))
            print(f"Processing batch: tracks {start_index + 1} to {end_index} (max 199 per batch)")
            
            # Process only tracks after those already present
            titles = []
            added_count = 0
            skipped_count = 0
            
            for i in range(start_index, end_index):
                video_id, video_title = video_info_list[i]
                print(f"Processing: {video_title}")
                titles.append(video_title)
                
                # Search for the track on Spotify
                track_uri = search_spotify_track(spotify_client, video_title)
                
                if track_uri:
                    # Check if the track is already in the playlist (double check for safety)
                    if track_uri not in existing_track_uris:
                        # Add to Spotify playlist
                        success = add_track_to_spotify_playlist(spotify_client, spotify_playlist_id, track_uri)
                        if success:
                            added_count += 1
                            existing_track_uris.append(track_uri)  # Add to list to avoid duplicates
                        else:
                            skipped_count += 1
                    else:
                        print(f"⚠️ Skipped: {video_title} (already in playlist)")
                        skipped_count += 1
                else:
                    skipped_count += 1
                    print(f"⚠️ Skipped: {video_title} (not found on Spotify)")
            
            print(f"✅ Added {added_count} new tracks, {skipped_count} skipped")
            print("Migration completed", titles)
            return titles
    except RuntimeError as e:
        raise RuntimeError(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main("")
