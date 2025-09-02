import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

class TorrentProcessor:
    def __init__(self, input_file: str = "generated/torrentsRaw.json", output_file: str = "generated/torrents.json", min_seeders: int = 5):
        """
        Initialize the TorrentProcessor
        
        Args:
            input_file: Path to the raw torrents JSON file
            output_file: Path for the processed torrents JSON file
            min_seeders: Minimum number of seeders to keep a torrent (default: 5)
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.min_seeders = min_seeders
        self.processed_torrents = []
        self.stats = {
            'total_input': 0,
            'removed_low_seeders': 0,
            'removed_duplicates': 0,
            'batch_single_conflicts': 0,
            'final_count': 0
        }
    
    def parse_episode_info(self, title: str) -> Optional[Dict]:
        """
        Parse episode information from torrent title
        
        Returns:
            Dict with arc_name, episode_number, is_extended, quality, or None if can't parse
        """
        # Pattern for OnePace episodes: [One Pace][chapters] Arc Episode [quality][hash].ext
        # Examples:
        # [One Pace][1089-1090] Egghead 19 Extended [1080p][93B80191].mkv
        # [One Pace][1080-1081] Egghead 14 [1080p][3C0010BE].mkv
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
        
        return {
            'chapters': chapters,
            'arc_name': arc_name,
            'episode_number': int(episode_num) if episode_num else None,
            'is_extended': is_extended,
            'quality': quality,
            'full_episode_id': f"{arc_name}_{episode_num}" if episode_num else f"{arc_name}_batch"
        }
    
    def get_quality_score(self, quality: str) -> int:
        """
        Convert quality string to numeric score for comparison
        Higher score = better quality
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
    
    def parse_upload_date(self, date_str: str) -> datetime:
        """
        Parse upload date string to datetime object
        Expected format: "2025-08-29 13:09"
        """
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            # Fallback for different date formats
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                # If we can't parse, return a very old date so it gets filtered out
                return datetime(1970, 1, 1)
    
    def is_duplicate_episode(self, torrent1: Dict, torrent2: Dict) -> bool:
        """
        Check if two torrents represent the same episode
        """
        info1 = self.parse_episode_info(torrent1['title'])
        info2 = self.parse_episode_info(torrent2['title'])
        
        if not info1 or not info2:
            return False
        
        # Same arc and episode number (considering extended versions)
        same_arc = info1['arc_name'] == info2['arc_name']
        same_episode = info1['episode_number'] == info2['episode_number']
        
        # Extended vs non-extended are considered different episodes
        same_extended = info1['is_extended'] == info2['is_extended']
        
        return same_arc and same_episode and same_extended
    
    def should_keep_torrent(self, current: Dict, existing: Dict) -> bool:
        """
        Determine which torrent to keep when duplicates are found
        Priority: newer upload date > better quality > more seeders
        """
        current_date = self.parse_upload_date(current['upload_date'])
        existing_date = self.parse_upload_date(existing['upload_date'])
        
        # If dates are different, keep the newer one
        if current_date != existing_date:
            return current_date > existing_date
        
        # If same date, compare quality
        current_info = self.parse_episode_info(current['title'])
        existing_info = self.parse_episode_info(existing['title'])
        
        if current_info and existing_info:
            current_quality = self.get_quality_score(current_info['quality'])
            existing_quality = self.get_quality_score(existing_info['quality'])
            
            if current_quality != existing_quality:
                return current_quality > existing_quality
        
        # If same quality, keep the one with more seeders
        return current['seeders'] > existing['seeders']
    
    def handle_batch_vs_single(self, torrents: List[Dict]) -> List[Dict]:
        """
        Handle conflicts between batch releases and individual episodes
        Keep both batch and newer individual episodes
        """
        result = []
        batch_torrents = []
        single_torrents = []
        
        # Separate batch and single torrents
        for torrent in torrents:
            if torrent['is_batch']:
                batch_torrents.append(torrent)
            else:
                single_torrents.append(torrent)
        
        # Add all batch torrents
        result.extend(batch_torrents)
        
        # For single episodes, check if there's a newer version than what's in batches
        for single in single_torrents:
            single_info = self.parse_episode_info(single['title'])
            if not single_info:
                result.append(single)
                continue
            
            # Check if this single episode conflicts with any batch
            conflicts_with_batch = False
            single_date = self.parse_upload_date(single['upload_date'])
            
            for batch in batch_torrents:
                batch_info = self.parse_episode_info(batch['title'])
                if batch_info and batch_info['arc_name'] == single_info['arc_name']:
                    batch_date = self.parse_upload_date(batch['upload_date'])
                    
                    # If single episode is newer than batch, keep both
                    # If batch is newer, skip the single episode
                    if single_date <= batch_date:
                        conflicts_with_batch = True
                        break
            
            if not conflicts_with_batch:
                result.append(single)
            else:
                # Check if single episode has better quality than batch
                single_quality = self.get_quality_score(single_info['quality'])
                should_keep = False
                
                for batch in batch_torrents:
                    batch_info = self.parse_episode_info(batch['title'])
                    if batch_info and batch_info['arc_name'] == single_info['arc_name']:
                        batch_quality = self.get_quality_score(batch_info['quality'])
                        if single_quality > batch_quality:
                            should_keep = True
                            break
                
                if should_keep:
                    result.append(single)
                    self.stats['batch_single_conflicts'] += 1
        
        return result
    
    def remove_duplicates(self, torrents: List[Dict]) -> List[Dict]:
        """
        Remove duplicate torrents, keeping the best version of each episode
        """
        result = []
        seen_episodes = {}
        
        # Sort torrents by upload date (newest first) for better duplicate handling
        sorted_torrents = sorted(torrents, 
                               key=lambda x: self.parse_upload_date(x['upload_date']), 
                               reverse=True)
        
        for torrent in sorted_torrents:
            torrent_info = self.parse_episode_info(torrent['title'])
            
            if not torrent_info:
                # Can't parse, just add it
                result.append(torrent)
                continue
            
            episode_key = torrent_info['full_episode_id']
            
            if episode_key not in seen_episodes:
                seen_episodes[episode_key] = torrent
                result.append(torrent)
            else:
                # Found duplicate, decide which to keep
                existing = seen_episodes[episode_key]
                if self.should_keep_torrent(torrent, existing):
                    # Replace existing with current
                    result.remove(existing)
                    result.append(torrent)
                    seen_episodes[episode_key] = torrent
                    self.stats['removed_duplicates'] += 1
                else:
                    self.stats['removed_duplicates'] += 1
        
        return result
    
    def filter_low_seeders(self, torrents: List[Dict]) -> List[Dict]:
        """
        Remove torrents with low seeder counts
        """
        result = []
        for torrent in torrents:
            if torrent['seeders'] >= self.min_seeders:
                result.append(torrent)
            else:
                self.stats['removed_low_seeders'] += 1
        
        return result
    
    def process_torrents(self) -> bool:
        """
        Main processing function
        
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
            self.stats['total_input'] = len(torrents)
            
            print(f"Processing {len(torrents)} torrents...")
            
            # Step 1: Filter out torrents with low seeders
            print(f"Step 1: Filtering torrents with less than {self.min_seeders} seeders...")
            torrents = self.filter_low_seeders(torrents)
            print(f"Remaining after seeder filter: {len(torrents)}")
            
            # Step 2: Remove duplicates
            print("Step 2: Removing duplicate episodes...")
            torrents = self.remove_duplicates(torrents)
            print(f"Remaining after duplicate removal: {len(torrents)}")
            
            # Step 3: Handle batch vs single episode conflicts
            print("Step 3: Handling batch vs single episode conflicts...")
            torrents = self.handle_batch_vs_single(torrents)
            print(f"Final count: {len(torrents)}")
            
            self.stats['final_count'] = len(torrents)
            self.processed_torrents = torrents
            
            # Create output data structure
            output_data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'source_file': str(self.input_file),
                    'processed_with': 'torrentProcessor.py',
                    'total_torrents_processed': self.stats['final_count'],
                    'processing_stats': self.stats,
                    'min_seeders_threshold': self.min_seeders,
                    'version': '1.0'
                },
                'torrents': torrents
            }
            
            # Ensure output directory exists
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save processed torrents
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error processing torrents: {e}")
            return False
    
    def print_stats(self):
        """
        Print processing statistics
        """
        print(f"\n=== Torrent Processing Statistics ===")
        print(f"Total input torrents: {self.stats['total_input']}")
        print(f"Removed (low seeders < {self.min_seeders}): {self.stats['removed_low_seeders']}")
        print(f"Removed (duplicates): {self.stats['removed_duplicates']}")
        print(f"Batch/single conflicts resolved: {self.stats['batch_single_conflicts']}")
        print(f"Final torrent count: {self.stats['final_count']}")
        print(f"Reduction: {self.stats['total_input'] - self.stats['final_count']} torrents removed")
        print(f"Output saved to: {self.output_file}")

def main():
    """
    Main function with command line interface
    """
    import sys
    
    # Default settings
    input_file = "generated/torrentsRaw.json"
    output_file = "generated/torrentsClean.json"
    min_seeders = 5
    
    # Simple argument parsing
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python torrentProcessor.py [min_seeders]")
            print("  min_seeders: Minimum number of seeders to keep (default: 5)")
            print("  Use 0 to keep all torrents regardless of seeder count")
            return
        
        try:
            min_seeders = int(sys.argv[1])
        except ValueError:
            print("Error: min_seeders must be a number")
            return
    
    print(f"OnePace Torrent Processor")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Minimum seeders: {min_seeders}")
    print(f"{'='*50}")
    
    processor = TorrentProcessor(input_file, output_file, min_seeders)
    
    if processor.process_torrents():
        processor.print_stats()
        print("\nProcessing completed successfully!")
    else:
        print("Processing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
