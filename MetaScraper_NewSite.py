import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import json
import traceback
from datetime import datetime
import re

options = Options()
options.add_argument("--headless")  # Uncomment this line to run headless

driver = webdriver.Firefox(options=options)

driver.get("https://onepace.net/en/watch")

def parse_sources_to_array(sources_text):
    """Parse source string into array, splitting on commas and cleaning up"""
    if not sources_text:
        return []
    
    # Split by comma and clean up each item
    items = [item.strip() for item in sources_text.split(',')]
    # Remove empty items
    return [item for item in items if item]

def findArcDivs():
    try:
        # Find the Ordered List element with role="list" and class containing "*:last:min-h-screen"
        ol_element = driver.find_element(By.XPATH, "//ol[@role='list' and contains(@class, '*:last:min-h-screen')]")
        
        # Find only direct children List Item elements (not nested ones)
        li_elements = ol_element.find_elements(By.XPATH, "./li")

        # Extract the IDs, titles, and source information from each List Item element
        arc_data = []
        order_counter = 1  # For chronological ordering
        all_available_qualities = set()  # Track all qualities found across all arcs
        all_available_types = set()  # Track all download types found across all arcs
        
        for li in li_elements:
            li_id = li.get_attribute("id")
            if li_id:  # Only process if the List Item has an id attribute
                # Find the anchor tag with href="#{id}"
                try:
                    anchor = li.find_element(By.XPATH, f".//a[@href='#{li_id}']")
                    title = anchor.text.strip()
                    
                    # Extract manga and anime sources
                    manga_sources = None
                    anime_sources = None
                    plot = None
                    background_img = None
                    highest_quality = None
                    links = {}
                    
                    try:
                        # Look for spans that contain "Manga Sources: " or "Anime Sources: " in sr-only spans
                        source_container_spans = li.find_elements(By.XPATH, ".//span[contains(@class, 'flex') and contains(@class, 'gap-x-')]")
                        
                        for container_span in source_container_spans:
                            container_text = container_span.text.strip().lower()
                            if "manga sources:" in container_text:
                                manga_sources = container_text.replace("manga sources:", "").strip()

                            elif "anime sources:" in container_text:
                                anime_sources = container_text.replace("anime sources:", "").strip()
                    
                        # Extract plot from the <p> tag
                        try:
                            plot_element = li.find_element(By.XPATH, ".//p[contains(@class, 'mt-2')]")
                            plot = plot_element.text.strip()
                        except Exception as plot_e:
                            pass  # Plot is optional
                            
                        # Extract background image URL
                        try:
                            img_element = li.find_element(By.XPATH, ".//img[@role='presentation']")
                            background_img = img_element.get_attribute("src")
                        except Exception as img_e:
                            pass  # Background image is optional
                            
                        # Extract all download links with quality and type information
                        try:
                            # Find all sections that contain download links (sub/dub/CC)
                            download_sections = li.find_elements(By.XPATH, ".//li[contains(@class, 'flex') and contains(@class, 'break-inside-avoid')]")
                            
                            for section in download_sections:
                                # Get the section type (sub/dub/CC)
                                try:
                                    section_header = section.find_element(By.XPATH, ".//span[@class='flex-1']")
                                    section_type = section_header.text.strip()
                                    
                                    # Simplify section type names
                                    if "English Subtitles" in section_type:
                                        section_key = "Sub"
                                    elif "English Dub with Closed Captions" in section_type:
                                        section_key = "Dub+CC"
                                    elif "English Dub" in section_type:
                                        section_key = "Dub"
                                    else:
                                        section_key = section_type
                                    
                                    # Initialize the section in links if not exists
                                    if section_key not in links:
                                        links[section_key] = {}
                                    
                                    # Find all download links in this section
                                    link_elements = section.find_elements(By.XPATH, ".//a[contains(@class, 'bg-gray-50/15')]")
                                    
                                    for link_element in link_elements:
                                        try:
                                            url = link_element.get_attribute("href")
                                            quality_span = link_element.find_element(By.XPATH, ".//span[contains(text(), 'p')]")
                                            quality = quality_span.text.strip()
                                            
                                            # Ensure we only store valid data
                                            if url and quality:
                                                links[section_key][quality] = str(url)
                                            
                                        except Exception as link_e:
                                            continue  # Skip malformed links
                                            
                                except Exception as section_e:
                                    continue  # Skip malformed sections
                            
                            # Extract highest quality from all available links
                            all_qualities = []
                            for section in links.values():
                                for quality in section.keys():
                                    if 'p' in quality:
                                        quality_num = quality.replace('p', '').strip()
                                        if quality_num.isdigit():
                                            all_qualities.append(int(quality_num))
                            
                            if all_qualities:
                                highest_quality = f"{max(all_qualities)}p"
                                
                        except Exception as quality_e:
                            pass  # Quality information is optional
                                
                    except Exception as e:
                        print(f"Warning: Could not extract all metadata for '{li_id}': {e}")
                    
                    # Build arc_info object, only including non-null values
                    # Determine type based on title
                    arc_type = "special" if title and "Special" in title else "arc"
                    
                    arc_info = {
                        "order": order_counter,
                        "type": arc_type
                    }
                    
                    # Only add fields if they have valid values
                    if li_id:
                        arc_info["id"] = str(li_id)
                    if title:
                        arc_info["title"] = str(title)
                    if manga_sources:
                        arc_info["manga_sources"] = parse_sources_to_array(manga_sources)
                    if anime_sources:
                        arc_info["anime_sources"] = parse_sources_to_array(anime_sources)
                    if plot:
                        arc_info["plot"] = str(plot)
                    if background_img:
                        arc_info["background_img"] = str(background_img)
                    if highest_quality:
                        arc_info["highest_quality"] = str(highest_quality)
                    if links:
                        arc_info["links"] = links
                        
                        # Track all qualities found
                        for section in links.values():
                            for quality in section.keys():
                                if 'p' in quality:
                                    all_available_qualities.add(quality)
                        
                        # Track all types found
                        for section_type in links.keys():
                            all_available_types.add(section_type)
                    
                    arc_data.append(arc_info)
                    order_counter += 1
                    
                    # Count total links for display
                    total_links = sum(len(section) for section in links.values())
                    print(f"✓ Processed: {title} ({li_id}) - Quality: {highest_quality or 'N/A'}, Links: {total_links}")
                except Exception as e:
                    print(f"✗ Failed to process arc '{li_id}': {e}")
                    # Still add the ID even if we can't find the title, but only if li_id exists
                    if li_id:
                        arc_data.append({
                            "order": order_counter,
                            "type": "arc",  # Default to arc if we can't determine title
                            "id": str(li_id)
                        })
                        order_counter += 1

        print(f"\n📊 Summary: Found {len(li_elements)} arcs, successfully processed {len([a for a in arc_data if a.get('title')])}")
        
        # Create metadata with quality information
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "source_url": "https://onepace.net/en/watch",
            "total_arcs": len(arc_data),
            "version": "1.0"
        }
        
        # Add quality and type info if we found any
        #if all_available_qualities:
        #    sorted_qualities = sorted(all_available_qualities, key=lambda x: int(x.replace('p', '')) if x.replace('p', '').isdigit() else 0)
        #    metadata["available_qualities"] = sorted_qualities
        #    
        #if all_available_types:
        #    metadata["available_types"] = sorted(list(all_available_types))
        
        return {"metadata": metadata, "arcs": arc_data}
    except Exception as e:
        print(f"❌ Error finding arc list: {e}")
        traceback.print_exc()
        return []

# Call the function and store the results
if __name__ == "__main__":
    try:
        print("🚀 Starting One Pace arc scraper...")
        print("⏳ Loading page and waiting for content...")
        
        # Wait a moment for the page to load
        import time
        time.sleep(3)
        
        # Find the arc data
        arc_data = findArcDivs()
        
        # Save the data to a JSON file
        if arc_data and arc_data.get("arcs"):
            
            os.makedirs("generated", exist_ok=True)
            with open("generated/siteMetadata.json", "w") as f:
                json.dump(arc_data, f, indent=2)
            print(f"💾 Saved {len(arc_data['arcs'])} arc entries to siteMetadata.json")
        else:
            print("⚠️  No arc data found")
            
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        traceback.print_exc()
    finally:
        print("🔄 Closing browser...")
        # Close the browser
        driver.quit()
        print("✅ Scraping complete!")