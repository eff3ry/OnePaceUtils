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
    
    def parse_arc_info(self, title: str, is_batch: bool = False) -> Optional[Dict]:
        """
        Parse arc information from torrent title to determine folder structure
        
        Returns:
            Dict with arc_name, episode_number, quality info, or None if can't parse
        """
        # Pattern for standard OnePace episodes: [One Pace][chapters] Arc Episode [quality][hash].ext
        # Examples:
        # [One Pace][1089-1090] Egghead 19 Extended [1080p][93B80191].mkv
        # [One Pace][903-908] Reverie [1080p]
        
        pattern = r'\[One Pace\]\[([^\]]+)\]\s*([^0-9\[]+?)\s*(\d+)?\s*(Extended)?\s*\[([^\]]+)\]'
        match = re.search(pattern, title)
        
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
            # Use the batch torrent name as the folder name (without file extension)
            folder_name = self.sanitize_filename(title)
            # Remove file extension if present
            if folder_name.endswith('.mkv') or folder_name.endswith('.mp4'):
                folder_name = folder_name.rsplit('.', 1)[0]
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
        path = Path(filename)
        
        # Check if it has a video extension
        if path.suffix.lower() in self.video_extensions:
            return str(path.with_suffix('.nfo'))
        else:
            # If no video extension, assume it's a batch and add .nfo
            return filename + '.nfo'
    
    def create_nfo_content(self, torrent: Dict, arc_info: Dict) -> str:
        """
        Create basic NFO file content for the episode
        """
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
        Process a batch torrent - create NFO for the batch file itself
        """
        nfo_files_created = 0
        
        # Create NFO for the batch torrent
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
                
                if batch_torrents:
                    # Use batch torrent name as folder name
                    batch_torrent, batch_info = batch_torrents[0]  # Use first batch torrent
                    folder_name = self.sanitize_filename(batch_torrent['title'])
                    # Remove file extension if present
                    if folder_name.endswith('.mkv') or folder_name.endswith('.mp4'):
                        folder_name = folder_name.rsplit('.', 1)[0]
                else:
                    # Create combined chapter range for single episodes
                    if single_torrents:
                        # Extract all chapter ranges and combine them
                        all_chapters = []
                        quality = single_torrents[0][1]['quality']  # Use quality from first episode
                        
                        for torrent, info in single_torrents:
                            chapters = info['chapters']
                            # Parse chapter range but preserve the original format for folder naming
                            
                            # Handle complex formats like "264-266, 268" (range + comma-separated)
                            if ',' in chapters:
                                # Split by comma first
                                parts = chapters.split(',')
                                for part in parts:
                                    part = part.strip()
                                    if '-' in part:
                                        # This part is a range
                                        start, end = part.split('-')
                                        all_chapters.extend([int(start.strip()), int(end.strip())])
                                    else:
                                        # This part is a single chapter
                                        all_chapters.append(int(part))
                            elif '-' in chapters:
                                # Simple range like "1089-1090"
                                start, end = chapters.split('-')
                                all_chapters.extend([int(start.strip()), int(end.strip())])
                            else:
                                # Single chapter
                                all_chapters.append(int(chapters.strip()))
                        
                        # For folder naming, we need to check if we have non-contiguous chapters
                        # If any torrent has comma-separated chapters, preserve that format
                        has_comma_separated = any(',' in info['chapters'] for torrent, info in single_torrents)
                        
                        if has_comma_separated:
                            # Collect all unique chapters and sort them numerically
                            all_chapter_nums = set()
                            for torrent, info in single_torrents:
                                chapters = info['chapters']
                                # Parse all chapter numbers from this torrent
                                if ',' in chapters:
                                    parts = chapters.split(',')
                                    for part in parts:
                                        part = part.strip()
                                        if '-' in part:
                                            start, end = part.split('-')
                                            all_chapter_nums.update(range(int(start.strip()), int(end.strip()) + 1))
                                        else:
                                            all_chapter_nums.add(int(part))
                                elif '-' in chapters:
                                    start, end = chapters.split('-')
                                    all_chapter_nums.update(range(int(start.strip()), int(end.strip()) + 1))
                                else:
                                    all_chapter_nums.add(int(chapters.strip()))
                            
                            # Sort chapters numerically and create comma-separated string
                            sorted_chapters = sorted(all_chapter_nums)
                            
                            # Group consecutive chapters into ranges, merge ranges with gaps of 5 or fewer chapters
                            chapter_groups = []
                            if sorted_chapters:
                                current_start = sorted_chapters[0]
                                current_end = sorted_chapters[0]
                                
                                for i in range(1, len(sorted_chapters)):
                                    gap = sorted_chapters[i] - current_end - 1
                                    if gap <= 5:  # Allow up to 5 chapters to be skipped
                                        # Small gap or consecutive, extend current range
                                        current_end = sorted_chapters[i]
                                    else:
                                        # Large gap, finish current range and start new one
                                        if current_start == current_end:
                                            chapter_groups.append(str(current_start))
                                        else:
                                            chapter_groups.append(f"{current_start}-{current_end}")
                                        current_start = sorted_chapters[i]
                                        current_end = sorted_chapters[i]
                                
                                # Add the last range
                                if current_start == current_end:
                                    chapter_groups.append(str(current_start))
                                else:
                                    chapter_groups.append(f"{current_start}-{current_end}")
                            
                            # Join with commas and spaces
                            combined_chapters = ', '.join(chapter_groups)
                            folder_name = f"[One Pace][{combined_chapters}] {arc_name} [{quality}]"
                        else:
                            # Find min and max chapters for contiguous ranges
                            min_chapter = min(all_chapters)
                            max_chapter = max(all_chapters)
                            
                            # Create folder name with combined range
                            if min_chapter == max_chapter:
                                folder_name = f"[One Pace][{min_chapter}] {arc_name} [{quality}]"
                            else:
                                folder_name = f"[One Pace][{min_chapter}-{max_chapter}] {arc_name} [{quality}]"
                        
                        folder_name = self.sanitize_filename(folder_name)
                    else:
                        continue  # Skip if no torrents
                
                final_arcs[folder_name] = arc_torrents
            
            print(f"Created {len(final_arcs)} folder structures")
            
            # Process each arc folder
            for folder_name, arc_torrents in final_arcs.items():
                print(f"\nProcessing folder: {folder_name}")
                
                # Create arc folder
                arc_folder = self.output_base / folder_name
                arc_folder.mkdir(parents=True, exist_ok=True)
                self.stats['directories_created'] += 1
                
                # Get arc name for season.nfo (use original arc name from first torrent)
                first_arc_info = arc_torrents[0][1]
                arc_name = first_arc_info['original_arc_name']
                
                # Create season.nfo for the arc
                season_nfo_path = arc_folder / "season.nfo"
                season_content = self.create_season_nfo_content(arc_name, [t[0] for t in arc_torrents])
                
                try:
                    with open(season_nfo_path, 'w', encoding='utf-8') as f:
                        f.write(season_content)
                    self.stats['nfo_files_created'] += 1
                    print(f"  Created season.nfo")
                except Exception as e:
                    print(f"  Error creating season.nfo: {e}")
                
                # Process each torrent in the arc
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
    input_file = "generated/torrentsClean.json"
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
