from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import json
import traceback
import os

options = Options()
options.add_argument("--headless")

driver = webdriver.Firefox(options=options)

driver.get("http://web.archive.org/web/20240616125537/https://onepace.net/watch")

try:
    divs = driver.find_elements(By.CLASS_NAME, "Carousel_root__By4Fm")

    arcsDiv = divs[0]
    arcButtons = arcsDiv.find_elements(By.CLASS_NAME, "Carousel_arc__CaVBH")

    arcInfosList = []

    for arcButton in arcButtons:
        arc = {}

        #try to click the Arc Poster to load information
        #if the poster is obscured error will throw so click the next page button to unobscure it
        try:
            arcButton.click()
        except Exception as e:
            arcsDiv.find_element(By.CLASS_NAME, "CarouselSlider_next___EQlV").click()
            arcButton.click()

        arcInfoDiv = arcsDiv.find_element(By.CLASS_NAME, "Carousel_infoContainer__nQFOf")
        
        arcNumber = arcButton.find_element(By.CLASS_NAME, "Carousel_part__noLrj").text
        arcName = arcInfoDiv.find_element(By.TAG_NAME, "h3").text
        print(f'Getting Info for Arc: {arcName}')
        arcDesc = arcInfoDiv.find_element(By.CLASS_NAME, "Carousel_description__ZmViu").text
        
        arc.update({'arcNumber' : arcNumber, 'arcName' : arcName, 'arcDesc' : arcDesc})

        arcInfoParagraphs = arcInfoDiv.find_elements(By.TAG_NAME, 'p')
        arcInfo = {}
        for info in arcInfoParagraphs[1:]:
            text = info.text
            arcInfo.update({text.split(':', 1)[0] : text.split(':', 1)[1]})
        
        arcLength = arcInfo['Duration'].strip()
        arc.update({'arcLength' : arcLength})

        arcRes = arcInfo['Resolution'].strip()
        arc.update({'arcRes' : arcRes})

        arcRelease = arcInfo['Released on'].strip()
        arc.update({'arcRelease' : arcRelease})

        arcSubs = []
        arcSubs = arcInfo['Subtitle language(s)'].strip().split(', ')
        arc.update({'arcSubs' : arcSubs})

        arcDubs = []
        arcDubs = arcInfo['Dub language(s)'].strip().split(', ')
        arc.update({'arcDubs' : arcDubs})
        
        #arcLinks = {}
        #arcLinkButtons = arcInfoDiv.find_element(By.CLASS_NAME, "Carousel_buttons__GB2gF").find_elements(By.TAG_NAME, 'div')
        #for button in arcLinkButtons:
        #    link = button.find_element(By.TAG_NAME, 'a').get_attribute('href')
        #    text = button.find_element(By.TAG_NAME, 'button').text
        #    if 'MAGNET' in text.upper():
        #        text = 'MAGNET LINK'
        #    arcLinks.update({text.upper() : link})

        #print(arcLinks)

        #try:
        #    arc.update({'magnetLink' : arcLinks['MAGNET LINK']})
        #except:
        #    print(f'MagnetLink not found for Arc: {arcName}')

        arcInfosList.append(arc)
        
    arcsEpisodes = {}
    for div in divs[1:]:
        arcName = div.find_element(By.TAG_NAME, "h2").find_element(By.TAG_NAME, "div").text
        epButtons = div.find_elements(By.CLASS_NAME, "CarouselSliderItem_item__eluWd")

        arcEps = []

        for button in epButtons:
            ep = {}

            try:
                button.click()
            except Exception as e:
                div.find_element(By.CLASS_NAME, "CarouselSlider_next___EQlV").click()
                button.click()
            
            epInfoDiv = div.find_element(By.CLASS_NAME, "Carousel_infoContainer__nQFOf")

            #info avaliable
            #Ep No in arc
            #ep name
            #ep desc

            #Manga Chapter(s): 1
            #Anime Episode(s): Episode of East Blue, 312 (Intro)
            #Duration: 18:17
            #Resolution: 1080p
            #Released on: 12/3/2020
            #Dub language(s): English, Japanese
            #Subtitle language(s): Arabic, German, English, Spanish, French

            #most episodes have this info so no need to do a try statement
            epNumber = button.find_element(By.CLASS_NAME, "Carousel_part__noLrj").text
            epName = epInfoDiv.find_element(By.TAG_NAME, "h3").text
            epDesc = epInfoDiv.find_element(By.CLASS_NAME, "Carousel_description__ZmViu").text

            print(f'Getting Info for episode: {epName}')
        
            ep.update({'epNumber' : epNumber, 'epName' : epName, 'epDesc' : epDesc})

            epInfoParagraphs = epInfoDiv.find_elements(By.TAG_NAME, 'p')
            epInfo = {}
            for info in epInfoParagraphs[1:]:
                text = info.text
                epInfo.update({text.split(':', 1)[0] : text.split(':', 1)[1]})
                
            epLength = epInfo['Duration'].strip()
            ep.update({'epLength' : epLength})

            epRes = epInfo['Resolution'].strip()
            ep.update({'epRes' : epRes})

            epRelease = epInfo['Released on'].strip()
            ep.update({'epRelease' : epRelease})

            epSubs = []
            epSubs = epInfo['Subtitle language(s)'].strip().split(', ')
            ep.update({'epSubs' : epSubs})

            epDubs = []
            epDubs = epInfo['Dub language(s)'].strip().split(', ')
            ep.update({'epDubs' : epDubs})

            #epLinks = {}
            #epLinkButtons = epInfoDiv.find_element(By.CLASS_NAME, "Carousel_buttons__GB2gF").find_elements(By.TAG_NAME, 'div')
            #for button in epLinkButtons:
            #    link = button.find_element(By.TAG_NAME, 'a').get_attribute('href')
            #    text = button.find_element(By.TAG_NAME, 'button').text
            #    if 'MAGNET' in text.upper():
            #        text = 'MAGNET LINK'
            #    epLinks.update({text.upper() : link})

            #print(arcLinks)

            #try:
            #    ep.update({'magnetLink' : epLinks['MAGNET LINK']})
            #except:
            #    print(f'MagnetLink not found for Episode: {epName}')

            arcEps.append(ep)
        arcsEpisodes.update({arcName : arcEps})

    #connect the episodes to the arc info
    for arc in arcInfosList:
        arc.update({'episodes' : arcsEpisodes[arc['arcName']]})

        #remove duplicate magnetlinks
        #for ep in arc['episodes']:
        #    try:
        #        if ep['magnetLink'] == arc['magnetLink']:
        #            ep.pop('magnetLink')
        #    except:
        #        continue

    #print(arcInfosList)
    json_str = json.dumps(arcInfosList, indent=4)
    #print(json_str)

    saveDir = "generated/old/"

    os.makedirs(saveDir, exist_ok=True)

    with open(f"{saveDir}/siteMetadata.json", "w") as outfile:
        outfile.write(json_str)

except Exception as e:
    print(f"An error occurred: {e}")
    traceback.print_exc()

driver.close()