import json
import os
from pathlib import Path
import re

metaJsonFile = "./meta.json"
rootFolder = "./One Pace/"

import xml.etree.ElementTree as ET

def modify_plot_outline_nfo(nfo_path, new_plot, new_outline):
    tree = ET.parse(nfo_path)
    root = tree.getroot()

    # Modify <plot> tag
    plot_element = root.find("plot")
    if plot_element is not None:
        plot_element.text = new_plot

    # Modify <outline> tag
    outline_element = root.find("outline")
    if outline_element is not None:
        outline_element.text = new_outline

    # Save changes
    tree.write(nfo_path, encoding="utf-8", xml_declaration=True)
    print(f"Updated File: {nfo_path.name}, Tag: <plot,outline>, Value: {new_plot}")

def modify_single_nfo(nfo_path: Path, nfo_tag: str, value: str):
    tree = ET.parse(nfo_path)
    root = tree.getroot()

    # Modify <nfo_tag> tag 
    element = root.find(nfo_tag)
    if element is not None:
        element.text = value

    # Save changes
    tree.write(nfo_path, encoding="utf-8", xml_declaration=True)
    print(f"Updated File: {nfo_path.name}, Tag:{nfo_tag}, Value: {value}")

def update_season_description(nfo_path, description):
    choice = input("Do you want to update the season description? (Y/n): ").strip().lower()
    
    if choice in ("", "y", "yes"):  # Default to 'yes' if input is empty
        #print(f"Season description updated to: {description}")
        modify_plot_outline_nfo(nfo_path, description, description)
    else:
        print("Season description not updated.")

def get_nfo_episode_number(nfo_file):
    tree = ET.parse(nfo_file)
    root = tree.getroot()

    episode_element = root.find("episode")
    
    if episode_element is not None and episode_element.text.isdigit():
        return int(episode_element.text)  # Convert to an integer
    else:
        print(f"Warning: No valid episode number found in {nfo_file}")
        return None
    
def get_regex_episode_number(file_name):
    # Match the last two-digit or single-digit number before the first bracketed part (e.g., [1080p])
    match = re.search(r'\b(\d{2}|\d{1})\b(?=\s*\[)', file_name)
    
    if match:
        return int(match.group(1))  # Convert to integer
    else:
        print(f"Warning: No episode number found in {file_name}")
        return None


#load json file
with open(metaJsonFile) as f:
    meta = json.load(f)
    print("Metadata Loaded from Json")

for season in meta:
    print(season["arcNumber"] +": " + season["arcName"])
print("Pick a Arc to copy data from\nChoose from the above numbers: ")
targetSeasonNumber = input()

for season in meta:
    if season["arcNumber"] == targetSeasonNumber:
        targetSeasonMeta = season
        break
print("You chose '" + targetSeasonNumber + " : " + season["arcName"]+ "'")

subdirs = [d.name for d in Path(rootFolder).iterdir() if d.is_dir()]

# Find potential matches
matchResults = [v for v in subdirs if targetSeasonMeta["arcName"] in v]

# Choice Menu
if len(matchResults) == 1:
    print(f"Potential Match Found: {matchResults[0]}")
    choice = input("Is this correct? (Y/n): ").strip().lower()
    if choice != "n":
        targetDir = matchResults[0]
    else:
        matchResults.clear()  # Allow user to choose manually

else:  # If no match or user declined the single match
    print("Pick the correct Directory:")
    for i, result in enumerate(subdirs):
        print(f"{i}: {result}")

    dirChoice = input("Choose from above: ").strip()
    targetDir = subdirs[int(dirChoice)]

#update the season NFO metadata
seasonNfoFile = Path(rootFolder).joinpath(targetDir).joinpath("season.nfo")
update_season_description(seasonNfoFile, targetSeasonMeta["arcDesc"])



##TODO LINK NFO TO EP METADATA FOR EACH
nfo_files = [f.name for f in Path(rootFolder).joinpath(Path(targetDir)).glob("*.nfo")]


for file in nfo_files:
    if file != "season.nfo":
        #detect embedded episode number
        filePath = Path(rootFolder).joinpath(targetDir).joinpath(file)
        epNum = get_regex_episode_number(file)

        #internal NFO ep number is not set to the episode number in the season but its corresponding manga chapter number
        seasonEpisodesMeta = targetSeasonMeta["episodes"]
        episodeMeta = None
        for episode in seasonEpisodesMeta:
            if episode["epNumber"] == str(epNum):
                episodeMeta = episode
                break

        print(f"File: {file}, Detected ep number: {epNum}")
        print(f"Copy data from {targetSeasonMeta['arcName']}, ep {episodeMeta['epNumber']}?")
        choice = input("Is this correct? (Y/n): ").strip().lower()
        if choice in ("", "y", "yes"):  # Default to 'yes' if input is empty
            #copy data
            if episodeMeta["epDesc"] != "Description unavailable.":
                modify_plot_outline_nfo(filePath, episodeMeta["epDesc"], episodeMeta["epDesc"])
            modify_single_nfo(filePath, "title", episodeMeta["epName"])
            if (get_nfo_episode_number(filePath) != epNum):
                modify_single_nfo(filePath, "episode", str(epNum))

        


##TODO ASK TO DO ANOTHER SEASON