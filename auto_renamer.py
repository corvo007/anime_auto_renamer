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

blacklist = []

blacklist_file = pathlib.Path.expanduser(
    pathlib.Path("~/.config/auto_renamer/blacklist.json")
)

os.makedirs(blacklist_file.parent, exist_ok=True)

if pathlib.Path(blacklist_file).exists():
    with open(blacklist_file, "r", encoding="utf8") as f:
        blacklist = json.load(f)
else:
    with open(blacklist_file, "w", encoding="utf8") as f:
        json.dump(blacklist, f)


def save_blacklist():
    with open(blacklist_file, "w", encoding="utf8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=2)


def get_file_info(filepath: pathlib.Path):
    if not filepath.is_file():
        return {"status": "error", "code": -1, "reason": "not a file", "info": {}}
    if filepath.suffix not in video_file_ext:
        return {"status": "error", "code": -2, "reason": "not a video file", "info": {}}
    with open(filepath, "rb") as f:
        file_hash = hashlib.md5(f.read(16777216)).hexdigest()
    try:
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
    except Exception as e:
        return {
            "status": "error",
            "code": -3,
            "reason": f"acplay api error: {e}",
            "info": {},
        }
    if response.status_code == 200:
        return {"status": "success", "code": 0, "info": response.json()}
    else:
        return {
            "status": "error",
            "code": -3,
            "reason": f"acplay api error: HTTP {response.status_code}",
            "info": {},
        }


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
        true_res = 0
        if not file_info["info"]["isMatched"]:
            if file.absolute().as_posix() in blacklist:
                return
            print(f"error: no explicit match \033[0;36m {file} \033[0m")
            print(
                "\n".join(
                    [
                        f"{i}.\033[0;36m {x['animeTitle']} - {x['episodeTitle']} ({x['typeDescription']}) \033[0m"
                        for i, x in enumerate(file_info["info"]["matches"][:5], start=1)
                    ]
                )
            )
            true_res = input(
                "select a result from above, [S]kip, or [A]dd to the blacklist: (enter index) "
            )
            if true_res.capitalize() == "A":
                blacklist.append(file.absolute().as_posix())
                save_blacklist()
                print(f"add \033[0;36m {file} \033[0m into blacklist")
            if not true_res.isdigit():
                print(f"skip matching for \033[0;36m {file} \033[0m")
                return
            true_res = int(true_res) - 1
        animeTitle = invalid_file_char.sub(
            " ", file_info["info"]["matches"][true_res]["animeTitle"]
        )
        episodeTitle = invalid_file_char.sub(
            " ", file_info["info"]["matches"][true_res]["episodeTitle"]
        )
        if mode == 0:
            return {file: destination / f"{animeTitle} - {episodeTitle}{file_ext}"}
        elif mode == 1:
            return {file: destination / animeTitle / f"{episodeTitle}{file_ext}"}
        elif mode == 2:
            return {file: destination / animeTitle / f"{file_name}"}
    else:
        if file_info["code"] == -3:
            print("error:", file_info["reason"], f"\033[0;36m {file} \033[0m")
        return


def handle_file(path: str, mode: int, dry_run=False):
    file_infos = []
    if not path:
        path = pathlib.Path.cwd()
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
    dest = input("anime folder: (use current folder if empty)")
    mode = input(
        "rename mode: (0: only rename 1: rename and move 2: only move, default: 1)"
    )
    dry_run = input("dry run? (y/n): ") == "y"
    resp = handle_file(rf"{dest}", 1 if not mode else int(mode), dry_run)
    if dry_run:
        print(
            "result review:\n",
            json.dumps(
                [{str(k): str(v) for k, v in x.items()} for x in resp],
                indent=2,
                ensure_ascii=False,
            ),
        )
    print("done")
