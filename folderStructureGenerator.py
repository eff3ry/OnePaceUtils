import json
import re
from pathlib import Path
from typing import Dict, List, Optional

class FolderStructureGenerator:
    def __init__(self, input_file: str = "generated/torrentsClean.json", output_base: str = "OnePace_Structure"):
        """
        Initialize the FolderStructureGenerator
        
        Args:
            input_file: Path to the processed torrents JSON file
            output_base: Base directory name for the generated structure
        """
        self.input_file = Path(input_file)
        self.output_base = Path(output_base)
        self.video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        self.stats = {
            'total_torrents': 0,
            'batch_torrents': 0,
            'single_torrents': 0,
            'directories_created': 0,
            'nfo_files_created': 0,
            'skipped_files': 0
        }
    
    def clean_title(self, title: str) -> str:
        """
        Clean the title by removing file extensions and parenthetical notes
        
        Examples:
        [One Pace][67-68] Baratie 08 [1080p][D8C1FD62].mkv (formerly Baratie 09)
        -> [One Pace][67-68] Baratie 08 [1080p][D8C1FD62]
        """
        # Remove file extension if present
        for ext in self.video_extensions:
            if title.lower().endswith(ext):
                title = title[:-len(ext)]
                break
        
        # Remove audio-related tags: [Dual-Audio], [ENG-ESP], etc.
        title = re.sub(r'\s*\[Dual-Audio\]', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\[ENG-ESP\]', '', title, flags=re.IGNORECASE)
        
        # Remove parenthetical notes at the end (like "(formerly Baratie 09)")
        # Look for pattern: space + opening paren + content + closing paren at end
        title = re.sub(r'\s+\([^)]*\)$', '', title)
        
        return title.strip()
    
    def parse_arc_info(self, title: str, is_batch: bool = False) -> Optional[Dict]:
        """
        Parse arc information from torrent title to determine folder structure
        
        Returns:
            Dict with arc_name, episode_number, quality info, or None if can't parse
        """
        # Clean the title first - remove file extensions and parenthetical notes
        cleaned_title = self.clean_title(title)
        
        # Pattern for standard OnePace episodes: [One Pace][chapters] Arc Episode [quality][hash]
        # Examples:
        # [One Pace][1089-1090] Egghead 19 Extended [1080p][93B80191]
        # [One Pace][903-908] Reverie [1080p]
        
        pattern = r'\[One Pace\]\[([^\]]+)\]\s*([^0-9\[]+?)\s*(\d+)?\s*(Extended)?\s*\[([^\]]+)\]'
        match = re.search(pattern, cleaned_title)
        
        if not match:
            return None
        
        chapters = match.group(1)
        arc_name = match.group(2).strip()
        episode_num = match.group(3)
        is_extended = match.group(4) is not None
        quality = match.group(5)
        
        # Clean up arc name - remove trailing dashes and extra info
        if ' - ' in arc_name:
            arc_name = arc_name.split(' - ')[0].strip()
        
        # Handle arc names that end with parenthetical info
        if '(' in arc_name:
            arc_name = arc_name.split('(')[0].strip()
        
        # For batch torrents, use the torrent name format as folder name
        # For single episodes, create a standardized folder name format
        if is_batch:
            # Use the cleaned batch torrent name as the folder name
            folder_name = self.sanitize_filename(cleaned_title)
        else:
            # Create standardized folder name: [One Pace][chapters] Arc [quality]
            folder_name = f"[One Pace][{chapters}] {arc_name} [{quality}]"
            folder_name = self.sanitize_filename(folder_name)
        
        return {
            'chapters': chapters,
            'arc_name': arc_name,
            'folder_name': folder_name,
            'episode_number': int(episode_num) if episode_num else None,
            'is_extended': is_extended,
            'quality': quality,
            'original_arc_name': arc_name
        }
    
    def merge_adjacent_ranges(self, chapter_parts: List[str]) -> List[str]:
        """
        Merge adjacent or overlapping chapter ranges
        Examples: ['299-300', '301-302'] -> ['299-302']
                 ['115-117', '117-119'] -> ['115-119']
                 ['42', '22'] -> ['42', '22'] (preserve non-adjacent singles)
        """
        if not chapter_parts:
            return []
        
        # Parse ranges into (start, end) tuples
        parsed_ranges = []
        for part in chapter_parts:
            if '-' in part:
                start, end = part.split('-', 1)
                parsed_ranges.append((int(start.strip()), int(end.strip())))
            else:
                # Single chapter
                num = int(part.strip())
                parsed_ranges.append((num, num))
        
        # Sort by start position to properly detect adjacency and overlaps
        parsed_ranges.sort(key=lambda x: x[0])
        
        merged = []
        current_start, current_end = parsed_ranges[0]
        
        for i in range(1, len(parsed_ranges)):
            next_start, next_end = parsed_ranges[i]
            
            # Check if ranges are adjacent or overlapping
            if current_end + 1 >= next_start:
                # Merge ranges - extend current range to include next range
                current_end = max(current_end, next_end)
            else:
                # Gap too large, finalize current range
                if current_start == current_end:
                    merged.append(str(current_start))
                else:
                    merged.append(f"{current_start}-{current_end}")
                
                current_start, current_end = next_start, next_end
        
        # Add the final range
        if current_start == current_end:
            merged.append(str(current_start))
        else:
            merged.append(f"{current_start}-{current_end}")
        
        return merged
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe filesystem usage
        """
        # Remove or replace characters that aren't safe for filenames
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip()
        
        # Remove multiple spaces and replace with single space
        filename = re.sub(r'\s+', ' ', filename)
        
        # Remove trailing dots and spaces
        filename = filename.rstrip('. ')
        
        return filename
    
    def convert_video_to_nfo(self, filename: str) -> str:
        """
        Convert video file extension to .nfo
        """
        # Clean the filename first to remove dual audio tags and other unwanted content
        cleaned_filename = self.clean_title(filename)
        path = Path(cleaned_filename)
        
        # Check if it has a video extension
        if path.suffix.lower() in self.video_extensions:
            return str(path.with_suffix('.nfo'))
        else:
            # If no video extension, assume it's a batch and add .nfo
            return cleaned_filename + '.nfo'
    
    def select_best_episodes(self, arc_torrents: List[tuple]) -> Dict[int, tuple]:
        """
        For an arc with both batch and individual episodes, select the best quality version of each episode
        
        Args:
            arc_torrents: List of (torrent, arc_info) tuples for this arc
            
        Returns:
            Dict mapping episode_number -> (torrent, arc_info, source_type) for the best version of each episode
        """
        episode_options = {}  # episode_number -> [(torrent, arc_info, quality_score, source_type)]
        
        for torrent, arc_info in arc_torrents:
            quality_score = self.get_quality_score(arc_info['quality'])
            
            if torrent['is_batch']:
                # Extract episodes from batch file_list
                file_list = torrent.get('file_list', [])
                for file_info in file_list:
                    file_path = file_info.get('path', '')
                    if not file_path:
                        continue
                    
                    # Extract episode number from filename
                    episode_match = re.search(r'\s(\d+)\s+\[', file_path)
                    if episode_match:
                        episode_num = int(episode_match.group(1))
                        
                        if episode_num not in episode_options:
                            episode_options[episode_num] = []
                        
                        # Create individual episode info from batch file
                        individual_info = arc_info.copy()
                        individual_info['episode_number'] = episode_num
                        individual_info['original_filename'] = file_path
                        
                        episode_options[episode_num].append((torrent, individual_info, quality_score, 'batch'))
            else:
                # Individual episode
                episode_num = arc_info.get('episode_number')
                if episode_num:
                    if episode_num not in episode_options:
                        episode_options[episode_num] = []
                    
                    episode_options[episode_num].append((torrent, arc_info, quality_score, 'individual'))
        
        # Select best version for each episode
        best_episodes = {}
        for episode_num, options in episode_options.items():
            # Sort by quality (highest first), then by source type (prefer individual over batch if same quality)
            best_option = max(options, key=lambda x: (x[2], x[3] == 'individual'))
            torrent, arc_info, quality_score, source_type = best_option
            best_episodes[episode_num] = (torrent, arc_info, source_type)
            
        return best_episodes
    
    def get_quality_score(self, quality: str) -> int:
        """
        Convert quality string to numeric score for comparison
        """
        quality_scores = {
            '480p': 1,
            '720p': 2,
            '1080p': 3,
            '1440p': 4,
            '2160p': 5,
            '4K': 5
        }
        return quality_scores.get(quality, 0)
    
    def create_nfo_content(self, torrent: Dict, arc_info: Dict) -> str:
        episode_num = arc_info.get('episode_number', 1)
        arc_name = arc_info.get('original_arc_name', 'Unknown Arc')
        is_extended = arc_info.get('is_extended', False)
        
        # Generate episode title
        if episode_num:
            title = f"{arc_name} {episode_num:02d}"
            if is_extended:
                title += " Extended"
        else:
            title = f"{arc_name} Batch"
        
        nfo_content = f'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<episodedetails>
  <title>{title}</title>
  <showtitle>One Pace</showtitle>
  <episode>{episode_num if episode_num else 1}</episode>
  <plot></plot>
  <runtime></runtime>
  <studio>OnePace Team</studio>
</episodedetails>'''
        
        return nfo_content
    
    def create_season_nfo_content(self, arc_name: str, torrents_in_arc: List[Dict]) -> str:
        """
        Create season.nfo content for an arc
        """
        episode_count = len([t for t in torrents_in_arc if not t['is_batch']])
        
        season_content = f'''<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<season>
  <title>{arc_name}</title>
  <plot></plot>
  <lockdata>false</lockdata>
  <studio>OnePace Team</studio>
  <sorttitle></sorttitle>
</season>'''
        
        return season_content
    
    def process_batch_torrent(self, torrent: Dict, arc_info: Dict, arc_folder: Path) -> int:
        """
        Process a batch torrent - create NFO for each individual file in the batch
        """
        nfo_files_created = 0
        
        # Check if this batch torrent has a file_list
        file_list = torrent.get('file_list', [])
        
        if file_list:
            # Create NFO for each individual file in the batch
            for file_info in file_list:
                file_path = file_info.get('path', '')
                if not file_path:
                    continue
                
                # Parse the individual file to get episode info
                individual_arc_info = self.parse_arc_info(file_path, is_batch=False)
                if not individual_arc_info:
                    # If can't parse individual file, use batch info but try to extract episode number
                    individual_arc_info = arc_info.copy()
                    # Try to extract episode number from filename
                    episode_match = re.search(r'(\d+)', file_path)
                    if episode_match:
                        individual_arc_info['episode_number'] = int(episode_match.group(1))
                
                # Create NFO filename from the individual file
                nfo_filename = self.convert_video_to_nfo(file_path)
                nfo_path = arc_folder / nfo_filename
                
                # Create the NFO file
                nfo_content = self.create_nfo_content(torrent, individual_arc_info)
                
                try:
                    with open(nfo_path, 'w', encoding='utf-8') as f:
                        f.write(nfo_content)
                    nfo_files_created += 1
                    print(f"  Created individual NFO: {nfo_path.name}")
                except Exception as e:
                    print(f"  Error creating NFO {nfo_path}: {e}")
                    self.stats['skipped_files'] += 1
        else:
            # Fallback: create NFO for the batch torrent itself if no file_list
            nfo_filename = self.convert_video_to_nfo(torrent['title'])
            nfo_path = arc_folder / nfo_filename
            
            # Create the NFO file
            nfo_content = self.create_nfo_content(torrent, arc_info)
            
            try:
                with open(nfo_path, 'w', encoding='utf-8') as f:
                    f.write(nfo_content)
                nfo_files_created += 1
                print(f"  Created batch NFO: {nfo_path.name}")
            except Exception as e:
                print(f"  Error creating NFO {nfo_path}: {e}")
                self.stats['skipped_files'] += 1
        
        return nfo_files_created
    
    def process_single_torrent(self, torrent: Dict, arc_info: Dict, arc_folder: Path) -> int:
        """
        Process a single episode torrent - create NFO file
        """
        nfo_files_created = 0
        
        # Create NFO for the single episode
        nfo_filename = self.convert_video_to_nfo(torrent['title'])
        nfo_path = arc_folder / nfo_filename
        
        # Create the NFO file
        nfo_content = self.create_nfo_content(torrent, arc_info)
        
        try:
            with open(nfo_path, 'w', encoding='utf-8') as f:
                f.write(nfo_content)
            nfo_files_created += 1
            print(f"  Created episode NFO: {nfo_path.name}")
        except Exception as e:
            print(f"  Error creating NFO {nfo_path}: {e}")
            self.stats['skipped_files'] += 1
        
        return nfo_files_created
    
    def generate_structure(self) -> bool:
        """
        Main function to generate the folder structure
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load input file
            if not self.input_file.exists():
                print(f"Error: Input file {self.input_file} not found")
                return False
            
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            torrents = data.get('torrents', [])
            self.stats['total_torrents'] = len(torrents)
            
            print(f"Generating folder structure from {len(torrents)} torrents...")
            print(f"Output directory: {self.output_base}")
            
            # Create base directory
            self.output_base.mkdir(parents=True, exist_ok=True)
            
            # Group torrents by arc name first, then create combined folder names
            arcs_by_name = {}
            
            for torrent in torrents:
                arc_info = self.parse_arc_info(torrent['title'], torrent['is_batch'])
                
                if not arc_info:
                    print(f"Warning: Could not parse torrent title: {torrent['title']}")
                    self.stats['skipped_files'] += 1
                    continue
                
                arc_name = arc_info['arc_name']
                
                if arc_name not in arcs_by_name:
                    arcs_by_name[arc_name] = []
                
                arcs_by_name[arc_name].append((torrent, arc_info))
            
            print(f"Found {len(arcs_by_name)} different arcs")
            
            # Create combined folder names for each arc
            final_arcs = {}
            
            for arc_name, arc_torrents in arcs_by_name.items():
                # Check if this arc has any batch torrents
                batch_torrents = [t for t in arc_torrents if t[0]['is_batch']]
                single_torrents = [t for t in arc_torrents if not t[0]['is_batch']]
                
                # Create a preliminary folder name
                if batch_torrents:
                    # For batch torrents, use the batch torrent's folder name as a starting point
                    batch_torrent, batch_info = batch_torrents[0]
                    folder_name = batch_info['folder_name']
                else:
                    # For single episodes only, we can calculate the final name now
                    if single_torrents:
                        # Collect all chapter strings and qualities
                        chapter_strings = []
                        quality = single_torrents[0][1]['quality']
                        
                        for torrent, info in single_torrents:
                            chapters = info['chapters']
                            if chapters not in chapter_strings:
                                chapter_strings.append(chapters)
                        
                        # Combine chapters
                        if len(chapter_strings) == 1:
                            combined_chapters = chapter_strings[0]
                        else:
                            all_chapter_parts = []
                            for chapter_str in chapter_strings:
                                if ',' in chapter_str:
                                    parts = [part.strip() for part in chapter_str.split(',')]
                                    all_chapter_parts.extend(parts)
                                else:
                                    all_chapter_parts.append(chapter_str)
                            
                            unique_parts = []
                            for part in all_chapter_parts:
                                if part not in unique_parts:
                                    unique_parts.append(part)
                            
                            merged_parts = self.merge_adjacent_ranges(unique_parts)
                            combined_chapters = ', '.join(merged_parts)
                        
                        folder_name = f"[One Pace][{combined_chapters}] {arc_name} [{quality}]"
                        
                        # Handle long folder names
                        if len(folder_name) > 200:
                            first_part = merged_parts[0] if 'merged_parts' in locals() else combined_chapters.split(',')[0]
                            last_part = merged_parts[-1] if 'merged_parts' in locals() else combined_chapters.split(',')[-1]
                            
                            if 'merged_parts' in locals() and len(merged_parts) > 2:
                                abbreviated_chapters = f"{first_part}, ... ({len(merged_parts)} ranges), {last_part}"
                            else:
                                abbreviated_chapters = combined_chapters
                            
                            folder_name = f"[One Pace][{abbreviated_chapters}] {arc_name} [{quality}]"
                        
                        folder_name = self.sanitize_filename(folder_name)
                    else:
                        continue
                
                final_arcs[folder_name] = arc_torrents
            
            print(f"Created {len(final_arcs)} folder structures")
            
            # Process each arc folder
            for folder_name, arc_torrents in final_arcs.items():
                print(f"\nProcessing folder: {folder_name}")
                
                # Get arc name for season.nfo (use original arc name from first torrent)
                first_arc_info = arc_torrents[0][1]
                arc_name = first_arc_info['original_arc_name']
                
                # Check if this arc has both batch and individual episodes
                has_batch = any(t[0]['is_batch'] for t in arc_torrents)
                has_individual = any(not t[0]['is_batch'] for t in arc_torrents)
                
                # Determine final folder name (may be updated for quality mix)
                final_folder_name = folder_name
                
                if has_batch and has_individual:
                    # Smart episode selection: choose best quality for each episode
                    print(f"  Arc has both batch and individual episodes - selecting best quality for each episode")
                    best_episodes = self.select_best_episodes(arc_torrents)
                    
                    # Calculate final folder name based on SELECTED episodes
                    qualities_used = set()
                    chapters_used = set()
                    
                    for episode_num, (torrent, arc_info, source_type) in best_episodes.items():
                        qualities_used.add(arc_info['quality'])
                        chapters_used.add(arc_info['chapters'])
                    
                    # Calculate combined chapters from selected episodes
                    if len(chapters_used) == 1:
                        combined_chapters = list(chapters_used)[0]
                    else:
                        all_chapter_parts = []
                        for chapter_str in sorted(chapters_used):
                            if ',' in chapter_str:
                                parts = [part.strip() for part in chapter_str.split(',')]
                                all_chapter_parts.extend(parts)
                            else:
                                all_chapter_parts.append(chapter_str)
                        
                        unique_parts = []
                        for part in all_chapter_parts:
                            if part not in unique_parts:
                                unique_parts.append(part)
                        
                        merged_parts = self.merge_adjacent_ranges(unique_parts)
                        combined_chapters = ', '.join(merged_parts)
                    
                    # Calculate quality string
                    if len(qualities_used) == 1:
                        quality_str = list(qualities_used)[0]
                        print(f"  All selected episodes are {quality_str}")
                    else:
                        sorted_qualities = sorted(qualities_used, key=lambda q: self.get_quality_score(q))
                        quality_str = f"{sorted_qualities[0]}-{sorted_qualities[-1]}"
                        print(f"  Mixed qualities: {', '.join(sorted_qualities)} -> using range {quality_str}")
                    
                    # Create final folder name
                    final_folder_name = f"[One Pace][{combined_chapters}] {arc_name} [{quality_str}]"
                    final_folder_name = self.sanitize_filename(final_folder_name)
                    
                    if folder_name != final_folder_name:
                        print(f"  Updated folder name based on selected episodes:")
                        print(f"    From: {folder_name}")
                        print(f"    To: {final_folder_name}")
                
                else:
                    # No conflict, use original folder name
                    final_folder_name = folder_name
                arc_folder = self.output_base / final_folder_name
                arc_folder.mkdir(parents=True, exist_ok=True)
                self.stats['directories_created'] += 1
                
                # Create season.nfo for the arc in the correct folder
                season_nfo_path = arc_folder / "season.nfo"
                season_content = self.create_season_nfo_content(arc_name, [t[0] for t in arc_torrents])
                
                try:
                    with open(season_nfo_path, 'w', encoding='utf-8') as f:
                        f.write(season_content)
                    self.stats['nfo_files_created'] += 1
                    print(f"  Created season.nfo")
                except Exception as e:
                    print(f"  Error creating season.nfo: {e}")
                
                if has_batch and has_individual:
                    # Process selected episodes (best_episodes already calculated above)
                    for episode_num in sorted(best_episodes.keys()):
                        torrent, arc_info, source_type = best_episodes[episode_num]
                        
                        if source_type == 'batch':
                            # Create NFO for this specific episode from batch
                            original_filename = arc_info.get('original_filename', '')
                            if original_filename:
                                nfo_filename = self.convert_video_to_nfo(original_filename)
                                nfo_path = arc_folder / nfo_filename
                                
                                nfo_content = self.create_nfo_content(torrent, arc_info)
                                
                                try:
                                    with open(nfo_path, 'w', encoding='utf-8') as f:
                                        f.write(nfo_content)
                                    self.stats['nfo_files_created'] += 1
                                    print(f"  Created NFO (from batch): {nfo_path.name} - Episode {episode_num} ({arc_info['quality']})")
                                except Exception as e:
                                    print(f"  Error creating NFO {nfo_path}: {e}")
                                    self.stats['skipped_files'] += 1
                        else:
                            # Individual episode
                            created = self.process_single_torrent(torrent, arc_info, arc_folder)
                            self.stats['nfo_files_created'] += created
                            print(f"  Selected individual episode {episode_num} ({arc_info['quality']}) over batch")
                    
                    # Update stats
                    batch_episodes = sum(1 for ep_num, (t, ai, st) in best_episodes.items() if st == 'batch')
                    individual_episodes = sum(1 for ep_num, (t, ai, st) in best_episodes.items() if st == 'individual')
                    
                    print(f"  Final selection: {individual_episodes} individual episodes, {batch_episodes} from batch")
                    print(f"  Quality range: {', '.join(sorted(qualities_used, key=lambda q: self.get_quality_score(q)))}")
                    
                else:
                    # Process normally - no conflicts to resolve
                    for torrent, arc_info in arc_torrents:
                        if torrent['is_batch']:
                            self.stats['batch_torrents'] += 1
                            created = self.process_batch_torrent(torrent, arc_info, arc_folder)
                        else:
                            self.stats['single_torrents'] += 1
                            created = self.process_single_torrent(torrent, arc_info, arc_folder)
                        
                        self.stats['nfo_files_created'] += created
            
            return True
            
        except Exception as e:
            print(f"Error generating structure: {e}")
            return False
    
    def print_stats(self):
        """
        Print generation statistics
        """
        print(f"\n=== Folder Structure Generation Statistics ===")
        print(f"Total torrents processed: {self.stats['total_torrents']}")
        print(f"Batch torrents: {self.stats['batch_torrents']}")
        print(f"Single episode torrents: {self.stats['single_torrents']}")
        print(f"Directories created: {self.stats['directories_created']}")
        print(f"NFO files created: {self.stats['nfo_files_created']}")
        print(f"Files skipped (parse errors): {self.stats['skipped_files']}")
        print(f"Output directory: {self.output_base.absolute()}")

def main():
    """
    Main function with command line interface
    """
    import sys
    
    # Default settings
    input_file = "generated/torrentsCleanAll.json"
    output_base = "OnePace_Structure"
    
    # Simple argument parsing
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python folderStructureGenerator.py [output_directory]")
            print("  output_directory: Base directory for generated structure (default: OnePace_Structure)")
            print("  Input file: generated/torrentsClean.json")
            return
        
        output_base = sys.argv[1]
    
    print(f"OnePace Folder Structure Generator")
    print(f"Input: {input_file}")
    print(f"Output: {output_base}")
    print(f"{'='*50}")
    
    generator = FolderStructureGenerator(input_file, output_base)
    
    if generator.generate_structure():
        generator.print_stats()
        print("\nFolder structure generation completed successfully!")
    else:
        print("Folder structure generation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
