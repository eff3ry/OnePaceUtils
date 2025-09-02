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
        self.base_url = "https://nyaa.si/user/Galaxy9000"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_page_count(self):
        """Get the total number of pages for the user"""
        try:
            response = self.session.get(f"{self.base_url}?p=1")
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
            
            # Find file list table
            file_list = []
            file_table = soup.find('table', class_='torrent-file-list')
            if file_table:
                rows = file_table.find('tbody').find_all('tr') if file_table.find('tbody') else []
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        file_path = cells[0].text.strip()
                        file_size = cells[1].text.strip()
                        file_list.append({
                            'path': file_path,
                            'size': file_size
                        })
            
            return file_list
        except Exception as e:
            print(f"Error extracting file list from {torrent_url}: {e}")
            return []
    
    def is_batch_torrent(self, title):
        """Determine if a torrent is a batch based on title analysis"""
        title_lower = title.lower()
        
        # Simple and reliable check: single files have extensions, batches don't
        # Common video file extensions
        video_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
        
        # If title ends with a video file extension, it's a single file
        if any(title_lower.endswith(ext) for ext in video_extensions):
            return False
        
        # If no file extension, it's a batch/folder
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
        url = f"{self.base_url}?p={page_num}"
        torrents = []
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find torrent table
            table = soup.find('table', class_='torrent-list')
            if not table:
                return torrents
            
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        continue
                    
                    # Extract torrent info
                    category_cell = cells[0]
                    title_cell = cells[1]
                    links_cell = cells[2]
                    size_cell = cells[3]
                    date_cell = cells[4]
                    seeders_cell = cells[5]
                    leechers_cell = cells[6] if len(cells) > 6 else None
                    
                    # Get title and torrent page link
                    title_link = title_cell.find('a')
                    if not title_link:
                        continue
                    
                    title = title_link.text.strip()
                    torrent_page_url = urllib.parse.urljoin("https://nyaa.si", title_link['href'])
                    
                    # Check if it's a OnePace file
                    if 'onepace' not in title.lower() and 'one pace' not in title.lower():
                        continue
                    
                    # Extract magnet link
                    print(f"Extracting magnet link for: {title}")
                    magnet_link = self.extract_magnet_link(torrent_page_url)
                    
                    # Determine if it's a batch torrent using improved logic
                    is_batch = self.is_batch_torrent(title)
                    
                    # Extract file list if it's a batch torrent
                    file_list = []
                    if is_batch:
                        print(f"Detected batch torrent, extracting file list...")
                        file_list = self.extract_file_list(torrent_page_url)
                    
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
                    print(f"Found: {title}")
                    
                    # Small delay to be respectful
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
            
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
            
            # Delay between pages
            time.sleep(1)
        
        return all_torrents
    
    def save_to_json(self, torrents, filename="torrentsRaw.json"):
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
                'uploader': 'Galaxy9000',
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
    
    print("Starting OnePace torrent scraper for Galaxy9000...")
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