import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time
import urllib.parse
import os

class NyaaScraper:
    def __init__(self):
        self.base_url = "https://nyaa.si/?f=0&c=0_0&q=one+pace"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_page_count(self):
        """Get the total number of pages for the query"""
        try:
            response = self.session.get(f"{self.base_url}&p=1")
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find pagination
            pagination = soup.find('ul', class_='pagination')
            if not pagination:
                return 1
            
            # Get the last page number
            page_links = pagination.find_all('a')
            if page_links:
                last_page = 1
                for link in page_links:
                    try:
                        page_num = int(link.text.strip())
                        last_page = max(last_page, page_num)
                    except ValueError:
                        continue
                return last_page
            return 1
        except Exception as e:
            print(f"Error getting page count: {e}")
            return 1
    
    def extract_magnet_link(self, torrent_url):
        """Extract magnet link from torrent page"""
        try:
            response = self.session.get(torrent_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find magnet link
            magnet_link = soup.find('a', href=re.compile(r'^magnet:'))
            if magnet_link:
                return magnet_link['href']
            return None
        except Exception as e:
            print(f"Error extracting magnet link from {torrent_url}: {e}")
            return None
    
    def extract_file_list(self, torrent_url):
        """Extract file list from torrent page"""
        try:
            response = self.session.get(torrent_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find file list - nyaa.si uses a <ul> with data-show="yes"
            file_list = []
            
            # Look for the file list ul element
            file_ul = soup.find('ul', {'data-show': 'yes'})
            
            if file_ul:
                # Find all li elements containing files
                file_items = file_ul.find_all('li')
                print(f"Found {len(file_items)} file items in list")
                
                for item in file_items:
                    # Extract filename (text content excluding the size span)
                    size_span = item.find('span', class_='file-size')
                    if size_span:
                        # Get the text before the size span
                        file_path = item.get_text()
                        # Remove the size text from the end
                        size_text = size_span.get_text().strip()
                        file_path = file_path.replace(size_text, '').strip()
                        
                        # Remove the icon class text if present
                        if file_path.startswith('file'):
                            # Remove leading file icon text
                            file_path = re.sub(r'^[^\[]*\[', '[', file_path)
                        
                        # Clean up the size text (remove parentheses)
                        size_text = size_text.replace('(', '').replace(')', '').strip()
                        
                        if file_path and size_text:
                            file_list.append({
                                'path': file_path,
                                'size': size_text
                            })
                
                print(f"Extracted {len(file_list)} files from file list")
            else:
                print("No file list ul element found on torrent page")
            
            return file_list
            
        except Exception as e:
            print(f"Error extracting file list from {torrent_url}: {e}")
            return []
    
    def is_batch_torrent(self, title):
        """Determine if a torrent is a batch based on title analysis"""
        title_lower = title.lower()
        
        # Common video file extensions
        video_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
        
        # If title ends with a video file extension, it's definitely a single file
        if any(title_lower.endswith(ext) for ext in video_extensions):
            return False
        
        # Parse OnePace format to check for episode numbers
        # Pattern: [One Pace][chapters] Arc Episode [quality]
        onepace_pattern = r'\[One Pace\]\[([^\]]+)\]\s*([^0-9\[]+?)\s*(\d+)?\s*(Extended)?\s*\[([^\]]+)\]'
        match = re.search(onepace_pattern, title)
        
        if match:
            episode_num = match.group(3)  # Episode number
            
            # If there's an episode number, it's likely a single episode
            if episode_num:
                return False
            
            # If no episode number, it's likely a batch
            return True
        
        # Fallback: if we can't parse the OnePace format, assume it's a batch
        # This handles edge cases and non-standard formats
        return True
    
    def parse_size(self, size_text):
        """Parse size text into bytes"""
        if not size_text:
            return 0
        
        size_text = size_text.strip()
        size_units = {
            'B': 1,
            'KiB': 1024,
            'MiB': 1024**2,
            'GiB': 1024**3,
            'TiB': 1024**4
        }
        
        # Extract number and unit
        match = re.match(r'(\d+\.?\d*)\s*(\w+)', size_text)
        if match:
            size_value = float(match.group(1))
            size_unit = match.group(2)
            return int(size_value * size_units.get(size_unit, 1))
        return 0
    
    def scrape_page(self, page_num):
        """Scrape torrents from a specific page"""
        url = f"{self.base_url}&p={page_num}"
        print(f"Requesting: {url}")
        torrents = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            print(f"Response status: {response.status_code}")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find torrent table
            table = soup.find('table', class_='torrent-list')
            if not table:
                return torrents
            
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
            print(f"Found {len(rows)} total rows on page {page_num}")
            
            processed_count = 0
            skipped_count = 0
            skip_reasons = {
                'insufficient_data': 0,
                'no_title_link': 0,
                'not_onepace': 0,
                'processing_error': 0
            }
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        print(f"SKIPPED (insufficient data): Row has only {len(cells)} cells, expected at least 6")
                        skipped_count += 1
                        skip_reasons['insufficient_data'] += 1
                        continue
                    
                    # Extract torrent info
                    category_cell = cells[0]
                    title_cell = cells[1]
                    links_cell = cells[2]
                    size_cell = cells[3]
                    date_cell = cells[4]
                    seeders_cell = cells[5]
                    leechers_cell = cells[6] if len(cells) > 6 else None
                    
                    # Get title and torrent page link - exclude comment links specifically
                    title_link = title_cell.find('a', href=lambda href: href and '/view/' in href, class_=lambda cls: cls != 'comments')
                    if not title_link:
                        # Fallback: find any link that's not a comment link and has /view/ in href
                        all_links = title_cell.find_all('a')
                        title_link = next((link for link in all_links 
                                         if link.get('href') and '/view/' in link.get('href') 
                                         and link.get('class') != ['comments']), None)
                    
                    if not title_link:
                        print(f"SKIPPED (no title link): No torrent title link found in row")
                        skipped_count += 1
                        skip_reasons['no_title_link'] += 1
                        continue
                    
                    title = title_link.text.strip()
                    torrent_page_url = urllib.parse.urljoin("https://nyaa.si", title_link['href'])
                    
                    # Since we're scraping from Galaxy9000's user page, all torrents should be OnePace
                    # But let's add a more lenient check and log what we're skipping
                    title_lower = title.lower()
                    if 'onepace' not in title_lower and 'one pace' not in title_lower and '[one pace]' not in title_lower:
                        print(f"SKIPPED (not OnePace): '{title}' - Reason: Title doesn't contain 'onepace', 'one pace', or '[one pace]'")
                        skipped_count += 1
                        skip_reasons['not_onepace'] += 1
                        continue
                    
                    # Extract magnet link from the links column (much faster than separate request)
                    magnet_link = None
                    magnet_links = links_cell.find_all('a', href=re.compile(r'^magnet:'))
                    if magnet_links:
                        magnet_link = magnet_links[0]['href']
                    
                    # Determine if it's a batch torrent using improved logic
                    is_batch = self.is_batch_torrent(title)
                    
                    # Extract file list if it's a batch torrent
                    file_list = []
                    if is_batch:
                        print(f"Detected batch torrent, extracting file list...")
                        try:
                            file_list = self.extract_file_list(torrent_page_url)
                            if file_list:
                                time.sleep(0.5)  # Brief delay after successful file list extraction
                        except Exception as e:
                            print(f"Warning: Failed to extract file list for '{title}': {e}")
                            # Continue processing without file list
                    
                    # Parse size
                    size_text = size_cell.text.strip()
                    size_bytes = self.parse_size(size_text)
                    
                    # Parse date
                    date_text = date_cell.text.strip()
                    
                    # Parse seeders
                    seeders = 0
                    try:
                        seeders = int(seeders_cell.text.strip()) if seeders_cell else 0
                    except ValueError:
                        seeders = 0
                    
                    # Parse leechers
                    leechers = 0
                    if leechers_cell:
                        try:
                            leechers = int(leechers_cell.text.strip())
                        except ValueError:
                            leechers = 0
                    
                    torrent_info = {
                        'title': title,
                        'magnet_link': magnet_link,
                        'file_size': {
                            'raw': size_text,
                            'bytes': size_bytes
                        },
                        'upload_date': date_text,
                        'seeders': seeders,
                        'leechers': leechers,
                        'is_batch': is_batch,
                        'torrent_page_url': torrent_page_url
                    }
                    
                    # Add file list for batch torrents
                    if is_batch and file_list:
                        torrent_info['file_list'] = file_list
                    
                    torrents.append(torrent_info)
                    processed_count += 1
                    print(f"Found: {title}")
                    
                    # Sleep was moved inside file list extraction above
                    
                except Exception as e:
                    print(f"SKIPPED (processing error): Error processing row - {e}")
                    skipped_count += 1
                    skip_reasons['processing_error'] += 1
                    continue
            
            print(f"Page {page_num} summary: {processed_count} processed, {skipped_count} skipped")
            if skipped_count > 0:
                print(f"  Skip breakdown:")
                if skip_reasons['insufficient_data'] > 0:
                    print(f"    - Insufficient data: {skip_reasons['insufficient_data']}")
                if skip_reasons['no_title_link'] > 0:
                    print(f"    - No title link: {skip_reasons['no_title_link']}")
                if skip_reasons['not_onepace'] > 0:
                    print(f"    - Not OnePace: {skip_reasons['not_onepace']}")
                if skip_reasons['processing_error'] > 0:
                    print(f"    - Processing errors: {skip_reasons['processing_error']}")
            
        except Exception as e:
            print(f"Error scraping page {page_num}: {e}")
        
        return torrents
    
    def scrape_all_pages(self):
        """Scrape all pages and return combined results"""
        print("Getting page count...")
        total_pages = self.get_page_count()
        print(f"Found {total_pages} pages to scrape")
        
        all_torrents = []
        
        for page in range(1, total_pages + 1):
            print(f"\nScraping page {page}/{total_pages}...")
            page_torrents = self.scrape_page(page)
            all_torrents.extend(page_torrents)
            print(f"Found {len(page_torrents)} OnePace torrents on page {page}")
            
            # Longer delay between pages to avoid rate limiting
            time.sleep(1.0)
        
        return all_torrents
    
    def save_to_json(self, torrents, filename="torrentsRawAll.json"):
        """Save torrent data to JSON file with metadata"""
        # Create generated directory if it doesn't exist
        generated_dir = "generated"
        if not os.path.exists(generated_dir):
            os.makedirs(generated_dir)
            print(f"Created directory: {generated_dir}")
        
        # Full path to the file
        filepath = os.path.join(generated_dir, filename)
        
        data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'source_url': self.base_url,
                'total_torrents_found': len(torrents),
                'version': '1.0',
            },
            'torrents': torrents
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nData saved to {filepath}")
        return filepath

def main():
    scraper = NyaaScraper()
    
    print("Starting OnePace torrent scraper...")
    print("This may take a while depending on the number of pages...")
    
    try:
        torrents = scraper.scrape_all_pages()
        
        if torrents:
            filename = scraper.save_to_json(torrents)
            print(f"\nScraping completed successfully!")
            print(f"Found {len(torrents)} OnePace torrents")
            print(f"Results saved to: {filename}")
            
            # Print summary
            batch_count = sum(1 for t in torrents if t['is_batch'])
            single_count = len(torrents) - batch_count
            print(f"\nSummary:")
            print(f"- Batch releases: {batch_count}")
            print(f"- Single episodes: {single_count}")
            
        else:
            print("No OnePace torrents found.")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
    except Exception as e:
        print(f"Error during scraping: {e}")

if __name__ == "__main__":
    main()