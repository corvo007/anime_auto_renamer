import json
import re
import requests
import os
import hashlib
try:
    import pathlib2 as pathlib
except ImportError:
    import pathlib
import shutil

video_file_ext = [".mp4", ".mkv", ".flv"]

invalid_file_char = re.compile(r"[\\/:*?\"<>|]")


def get_file_info(filepath: pathlib.Path):
    if not filepath.is_file():
        return {"status": "error", "reason": "not a file", "info": {}}
    if filepath.suffix not in video_file_ext:
        return {"status": "error", "reason": "not a video file", "info": {}}
    with open(filepath, "rb") as f:
        file_hash = hashlib.md5(f.read(16777216)).hexdigest()
    response = requests.post(
        url="https://api.acplay.net/api/v2/match",
        json={
            "fileName": filepath.name,
            "fileHash": file_hash,
            "fileSize": os.path.getsize(filepath),
        },
        headers={
            "Accept": "application/json",
            "User-Agent": "dandanplay/desktop 12.0.2.124",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    if response.status_code == 200:
        return {"status": "success", "info": response.json()}
    else:
        return {"status": "error", "reason": "acplay api error", "info": {}}


def generate_file_info(filepath: str, mode: int, destination: str = None):
    """
    mode: 0: only rename 1: rename and move 2: only move
    """
    destination = (
        pathlib.Path(filepath).absolute().parent
        if not destination
        else pathlib.Path(destination).absolute()
    )
    file = pathlib.Path(filepath)
    file_name = file.absolute().name
    file_ext = file.absolute().suffix
    file_info = get_file_info(file)
    if file_info["status"] == "success":
        if not file_info["info"]["isMatched"]:
            print("error: no explicit match", file)
            return
        animeTitle = invalid_file_char.sub(
            " ", file_info["info"]["matches"][0]["animeTitle"]
        )
        episodeTitle = invalid_file_char.sub(
            " ", file_info["info"]["matches"][0]["episodeTitle"]
        )
        if mode == 0:
            return {file: destination / f"{animeTitle} - {episodeTitle}{file_ext}"}
        elif mode == 1:
            return {file: destination / animeTitle / f"{episodeTitle}{file_ext}"}
        elif mode == 2:
            return {file: destination / animeTitle / f"{file_name}"}
    else:
        print("error:", file_info["reason"], file)
        return


def handle_file(path: str, mode: int, dry_run=False):
    file_infos = []
    for file in os.listdir(path):
        file_info = generate_file_info(os.path.join(path, file), mode)
        if file_info:
            file_infos.append(file_info)
    if dry_run:
        return file_infos
    else:
        for file in file_infos:
            src = list(file.keys())[0]
            dst = list(file.values())[0]
            print(src, "will be renamed (and move) as", dst)
            if not dst.parent.exists():
                dst.parent.mkdir(parents=True)
            shutil.move(src, dst)


if __name__ == "__main__":
    dest = input("anime folder: ")
    mode = int(input("rename mode: (0: only rename 1: rename and move 2: only move)"))
    dry_run = input("dry run? (y/n): ") == "y"
    resp = handle_file(rf"{dest}", mode, dry_run)
    if dry_run:
        print("result review:\n", json.dumps(resp, indent=2))
    print("done")
