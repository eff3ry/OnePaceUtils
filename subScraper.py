from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET
import json
import os
import re
import sys

rootFolder = Path("./OnePace_Structure")
subtitleTitleUrl = "https://github.com/one-pace/one-pace-public-subtitles/raw/refs/heads/main/main/title.properties"

def clear():
    if os.name == 'nt':
        _ = os.system('cls')
    else:
        _ = os.system('clear')

def mainMenu():
    i = input("Choose an option:\n1. Scrape Titles from official subtitle repo\n:")
    try:
        i = int(i)
    except:
        clear()
        print(f"Could not convert '{i}' to integer.")
        mainMenu()
        return
    
    match(i):
        case 1:
            scrapeSubtitles()


#Subtitle Functions
def find_best_folder_match(arc_name, subdirs):
    """
    Find the best matching folder for an arc name using various matching strategies.
    Returns a list with the best match, or empty list if no match found.
    """
    # Strategy 1: Exact substring match (original logic)
    exact_matches = [v for v in subdirs if arc_name in v]
    if exact_matches:
        return exact_matches
    
    # Strategy 2: Case-insensitive substring match
    case_insensitive_matches = [v for v in subdirs if arc_name.lower() in v.lower()]
    if case_insensitive_matches:
        return case_insensitive_matches
    
    # Strategy 3: Handle common name variations
    arc_name_variants = get_arc_name_variants(arc_name)
    for variant in arc_name_variants:
        variant_matches = [v for v in subdirs if variant.lower() in v.lower()]
        if variant_matches:
            return variant_matches
    
    # Strategy 4: Match first 3+ characters (for short arc names, use at least 3 chars)
    min_chars = min(3, len(arc_name))
    if len(arc_name) >= min_chars:
        prefix = arc_name[:min_chars].lower()
        prefix_matches = [v for v in subdirs if v.lower().startswith(prefix)]
        if prefix_matches:
            return prefix_matches
    
    # Strategy 5: Fuzzy matching - check if most words from arc name appear in folder name
    arc_words = set(arc_name.lower().split())
    best_match = None
    best_score = 0
    
    for folder in subdirs:
        folder_words = set(re.findall(r'\b\w+\b', folder.lower()))
        # Calculate how many arc words appear in the folder name
        matching_words = arc_words.intersection(folder_words)
        score = len(matching_words) / len(arc_words) if arc_words else 0
        
        # Require at least 50% of words to match
        if score > 0.5 and score > best_score:
            best_score = score
            best_match = folder
    
    return [best_match] if best_match else []

def get_arc_name_variants(arc_name):
    """
    Generate common variants of arc names to improve matching.
    """
    variants = []
    
    # Common replacements for known problematic arc names
    replacements = {
        "Alabasta": ["Arabasta"],
        "Water 7": ["Water Seven", "Water7", "Waterseven"],
        "Davy Back Fight": ["Davy Back", "Long Ring Long Land"],
        "Fishmen Island": ["Fish-Man Island", "Fishman Island", "Fish Man Island"],
        "Enies Lobby": ["Ennies Lobby", "Ennie's Lobby"],
        "Sabaody Archipelago": ["Sabaody", "Shabondy Archipelago"],
        "Amazon Lily": ["Amazon", "Lily"],
        "Post-War": ["Post War", "Postwar"],
        "Return to Sabaody": ["Return Sabaody"],
        "Punk Hazard": ["Punkhazard"],
        "Whole Cake Island": ["WCI", "Whole Cake"],
        "Whisky Peak": ["Whiskey Peak"],
    }
    
    if arc_name in replacements:
        variants.extend(replacements[arc_name])
    
    # Add hyphenated versions
    if " " in arc_name:
        variants.append(arc_name.replace(" ", "-"))
        variants.append(arc_name.replace(" ", ""))
    
    # Add versions without common words
    #common_words = ["arc", "saga", "island", "archipelago"]
    #for word in common_words:
    #   if word.lower() in arc_name.lower():
    #        variants.append(arc_name.replace(word, "").replace(word.title(), "").strip())
    
    return variants

def get_arc_resolution_pattern(target_dir):
    """
    Detect the resolution pattern from existing files in the arc directory.
    Returns the most common resolution pattern found, or '[TBD]' as fallback.
    """
    resolution_patterns = []
    
    # Look for resolution patterns in existing files
    for file in target_dir.glob("*.nfo"):
        if file.name != "season.nfo":
            # Extract resolution pattern like [1080p], [720p], etc.
            match = re.search(r'\[(\d+p)\]', file.name)
            if match:
                resolution_patterns.append(f"[{match.group(1)}]")
    
    if resolution_patterns:
        # Return the most common resolution pattern
        from collections import Counter
        most_common = Counter(resolution_patterns).most_common(1)
        return most_common[0][0]
    else:
        return "[TBDp]"

def create_nfo_file(target_dir, arc_name, episode_num, title):
    """
    Create a new NFO file for an episode that doesn't exist yet.
    """
    # Get resolution pattern from existing files in the arc
    resolution = "[TBDp]"#get_arc_resolution_pattern(target_dir)
    
    # Generate filename with placeholders (using characters valid for Windows filenames)
    filename = f"[One Pace][chTBD-TBD] {arc_name} {episode_num:02d} {resolution}[TBD].nfo"
    file_path = target_dir / filename
    
    # Create the basic NFO content
    nfo_content = f'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<episodedetails>
  <title>{title}</title>
  <showtitle>One Pace</showtitle>
  <episode>{episode_num}</episode>
</episodedetails>'''
    
    # Write the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(nfo_content)
    
    print(f"Created new NFO file: {filename}")
    return file_path

def scrapeSubtitles():
    subtitleText = download_properties_text(subtitleTitleUrl)
    if subtitleText is None:
        print(f"Failed to download text file from {subtitleTitleUrl}\nExiting...")
        sys.exit(1)
    subtitleDict = parse_title_properties_from_text(subtitleText)
    
    i = input("Auto Match Arcs? Y/n: ")
    if i.lower().strip() == "n":
        return
    
    subdirs = [d.name for d in rootFolder.iterdir() if d.is_dir()]

    matchDict = {}
    failedMatches = []
    for arcName in subtitleDict:
        #(arcName)
        matchResults = find_best_folder_match(arcName, subdirs)
        if len(matchResults) > 0:
            print(f"{matchResults[0]} is match for {arcName}")
            matchDict[arcName] = matchResults[0]
        else:
            print(f"No match for {arcName}")
            failedMatches.append(arcName)
        
    
    i = input("Manually match failed matches? Y/n: ")
    if i.lower().strip() != "n":
        manualMatch(failedMatches, subdirs, matchDict)

    titlesToReview = {}
    for arc in matchDict:
        arcTitlesToReview = {}
        #arc = Arc Name
        #matchDict[arc] = arc folder name
        #rootFolder.join(matchDict[arc]) = arc Path
        print(arc)

        targetDir = rootFolder.joinpath(matchDict[arc])
        print(targetDir)


        
        #TODO scan arc path for nfo files and update titles
        nfo_files = [f.name for f in targetDir.glob("*.nfo")]
        existing_episodes = set()
        
        for nfo_file in nfo_files:
            if nfo_file != "season.nfo":
                episodeToReview = {}
                epNum = get_regex_episode_number(nfo_file)
                if epNum != None:
                    #update internal ep number if incorrect
                    if str(epNum) != get_nfo_episode_number(targetDir.joinpath(nfo_file)):
                        set_nfo_episode_number(targetDir.joinpath(nfo_file), str(epNum))
                        print()

                if epNum == None:
                    epNum = get_nfo_episode_number(targetDir.joinpath(nfo_file))
                    #print(epNum)
                    try:
                        epNum = int(epNum)
                    except:
                        print("Failed to convert extracted episode number from NFO data to Integer. Skipping Episode...")
                        epNum = None

                if epNum != None:
                    existing_episodes.add(epNum)
                    currentTitle = get_nfo_title(targetDir.joinpath(nfo_file))
                    try:
                        scrapedTitle:str = subtitleDict[arc][epNum-1]
                    except:
                        scrapedTitle = ""
                    
                    # Check if this is an extended episode and modify the scraped title accordingly
                    if "Extended" in nfo_file and scrapedTitle and scrapedTitle != "":
                        scrapedTitle = scrapedTitle + " - Extended"
                    
                    if scrapedTitle  == "" or scrapedTitle == None:
                        print(f"{arc}, {epNum} : Could not find new title. Skipping...")
                    elif currentTitle == scrapedTitle:
                        print(f"{arc}, {epNum} : No changes to title were made")
                    else:
                        print(f"{arc}, {epNum} : title needs updating from '{currentTitle}' to '{scrapedTitle}'")
                        
                        episodeToReview["currentTitle"] = currentTitle
                        episodeToReview["newTitle"] = scrapedTitle
                        episodeToReview["nfoPath"] = str(targetDir.joinpath(nfo_file))
                        arcTitlesToReview[epNum] = episodeToReview
        
        # Check for missing episodes and offer to create them
        if arc in subtitleDict and len(subtitleDict[arc]) > 0:
            total_episodes = len(subtitleDict[arc])
            missing_episodes = []
            
            for ep_num in range(1, total_episodes + 1):
                if ep_num not in existing_episodes:
                    missing_episodes.append(ep_num)
            
            if missing_episodes:
                print(f"Missing episodes found for {arc}: {missing_episodes}")
                create_missing = input("Create NFO files for missing episodes? Y/n: ")
                if create_missing.lower().strip() != "n":
                    for ep_num in missing_episodes:
                        try:
                            title = subtitleDict[arc][ep_num-1]
                            if title and title.strip():
                                create_nfo_file(targetDir, arc, ep_num, title)
                            else:
                                print(f"Skipping episode {ep_num} - no title available")
                        except IndexError:
                            print(f"Skipping episode {ep_num} - index out of range")
        
        if len(arcTitlesToReview) > 0:
            titlesToReview[arc] = arcTitlesToReview
        print()
    #print(json.dumps(titlesToReview, indent=4))
    reviewTitleChanges(titlesToReview)

def reviewTitleChanges(titlesDict: dict):
    for arc in titlesDict:
        num_changes = len(titlesDict[arc])
        
        if num_changes == 1:
            # For single changes, show the change directly
            episode = list(titlesDict[arc].keys())[0]
            print(f"\n{arc}")
            print(f"Episode {episode}\nCurrent Title: {titlesDict[arc][episode]['currentTitle']}\nNew Title:     {titlesDict[arc][episode]['newTitle']}")
            i = input("Update Title? Y/n: ")
            if i.lower().strip() != "n":
                #update title
                set_nfo_title(Path(titlesDict[arc][episode]["nfoPath"]), titlesDict[arc][episode]['newTitle'])
        else:
            # For multiple changes, ask if user wants to review the arc first
            print(f"\n{arc}, {num_changes} changes recommended")
            i = input("Review? Y/n: ")
            if i.lower().strip() != "n":
                print(f"\n{arc}")
                for episode in titlesDict[arc]:
                    print(f"\nEpisode {episode}\nCurrent Title: {titlesDict[arc][episode]['currentTitle']}\nNew Title:     {titlesDict[arc][episode]['newTitle']}")
                    i = input("Update Title? Y/n: ")
                    if i.lower().strip() != "n":
                        #update title
                        set_nfo_title(Path(titlesDict[arc][episode]["nfoPath"]), titlesDict[arc][episode]['newTitle'])
            else:
                print(f"Skipping {arc}")
        print()

def set_nfo_title(nfo_path: Path, value: str):
    tree = ET.parse(nfo_path)
    root = tree.getroot()

    # Modify <nfo_tag> tag 
    element = root.find("title")
    if element is not None:
        element.text = value

    # Save changes
    tree.write(nfo_path, encoding="utf-8", xml_declaration=True)
    print(f"Updated File: {nfo_path.name}, Tag: title, Value: {value}")

def set_nfo_episode_number(nfo_path: Path, value: str):
    tree = ET.parse(nfo_path)
    root = tree.getroot()

    # Modify <nfo_tag> tag 
    element = root.find("episode")
    if element is not None:
        element.text = value

    # Save changes
    tree.write(nfo_path, encoding="utf-8", xml_declaration=True)
    print(f"Updated File: {nfo_path.name}, Tag: Episode, Value: {value}")

def get_nfo_episode_number(nfo_path: Path):
    tree = ET.parse(nfo_path)
    root = tree.getroot()

    # get <title> tag 
    element = root.find("episode")
    if element is not None:
        return element.text
    else:
        return None

def get_nfo_title(nfo_path: Path):
    tree = ET.parse(nfo_path)
    root = tree.getroot()

    # get <title> tag 
    element = root.find("title")
    if element is not None:
        return element.text
    else:
        return None

def get_regex_episode_number(file_name):
    # Try multiple patterns to extract episode number
    
    # Pattern 1: Number before [quality] (original pattern)
    match = re.search(r'\b(\d{2}|\d{1})\b(?=\s*\[)', file_name)
    if match:
        return int(match.group(1))
    
    # Pattern 2: One Pace format - number after arc name and before Extended/modifiers
    # Matches: "[One Pace][episodes] ArcName ## Extended [quality]"
    match = re.search(r'\b\w+\s+(\d{1,2})\s+(?:Extended|Director|Special|Final)', file_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Pattern 3: Number before "Extended" or similar modifiers (general case)
    match = re.search(r'\b(\d{2}|\d{1})\b(?=\s*(?:Extended|Director|Special|Final))', file_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Pattern 4: Number followed by space and then any non-digit word
    match = re.search(r'\b(\d{2}|\d{1})\b(?=\s+[A-Za-z])', file_name)
    if match:
        return int(match.group(1))
    
    # Pattern 5: Just find the last standalone number in the filename (fallback)
    matches = re.findall(r'\b(\d{1,2})\b', file_name)
    if matches:
        # Return the last number found, assuming it's the episode number
        return int(matches[-1])
    
    return None
        
def manualMatch(failedMatches: list, dirs: list, matchDict: dict):
    i = 0
    for arc in failedMatches:
        print(f"{i}. {arc}")
        i+=1
    i = input("Pick item to match, type 'done' if finished: ")
    if i.lower().strip() == 'done':
        return
    try:
        i = int(i)
    except:
        clear()
        print(f"Could not convert '{i}' to integer.")
        manualMatch(failedMatches, dirs, matchDict)
        return
    
    if i >= len(failedMatches) or i < 0:
        clear()
        print(f"{i} was out of range.")
        manualMatch(failedMatches, dirs, matchDict)
        return

    arcToMatch = failedMatches.pop(i)
    i = 0
    for dir in dirs:
        print(f"{i}. {dir}")
        i+=1
    i = input("Pick item to match: ")
    try:
        i = int(i)
    except:
        clear()
        print(f"Could not convert '{i}' to integer.")
        manualMatch(failedMatches, dirs, matchDict)
        return
    
    if i >= len(dirs) or i < 0:
        clear()
        print(f"{i} was out of range.")
        manualMatch(failedMatches, dirs, matchDict)
        return
    
    print(f"'{arcToMatch}' matched to '{dirs[i]}'")
    matchDict[arcToMatch] = dirs[i]
    if len(failedMatches) > 0:
        manualMatch(failedMatches, dirs, matchDict)
        return

def download_properties_text(url):
    """
    Downloads the properties file from the specified URL directly into memory.
    Returns the file's text content.
    """
    print(f"Downloading properties file from {url}")

    with urllib.request.urlopen(url) as response:
        data = response.read().decode("utf-8")

    return data

def parse_title_properties_from_text(text):
    """
    Parses the properties file content where comment lines (starting with '#')
    denote a new category and subsequent key=value lines contain episode titles.
    Returns a dictionary mapping category names to lists of episode titles.
    """
    titles_dict = {}
    current_category = None

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue  # Skip blank lines

        if line.startswith("#"):
            # New category: remove '#' and any extra whitespace.
            current_category = line.lstrip("#").strip()
            titles_dict[current_category] = []
        elif "=" in line:
            # Lines in the format: key=eptitle
            parts = line.split("=", 1)
            if len(parts) == 2:
                title = parts[1].strip()
                if current_category is not None:
                    titles_dict[current_category].append(title)

    return titles_dict


def main():
    mainMenu()

    #subdirs = [d.name for d in rootFolder.iterdir() if d.is_dir()]

    #for dir in subdirs:
    #    print(dir)

if __name__ == "__main__":
    scrapeSubtitles()