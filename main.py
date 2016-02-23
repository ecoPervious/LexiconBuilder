# -*- coding: utf-8 -*-
import os
import codecs
import requests
import Queue
import threading
import time
from bs4 import BeautifulSoup
from datetime import datetime

# -----------------------------------------------------------------------------------
# ------------Global variables
# -----------------------------------------------------------------------------------
baseUrl = "http://www.investopedia.com"
letterList = '1abcdefghijklmnopqrstuvwxyz'
# letterList = '1'
outDir = os.getcwd() + "/out/"
lock = threading.Lock()
dictionary = list()
fetchedCount = 0
totalCount = 0
warnCount = 0
###########https://docs.python.org/2/howto/logging.html

# -----------------------------------------------------------------------------------
# ------------Functions
# -----------------------------------------------------------------------------------
# open url and extact html object(soup)
def getSoup( url ):
    # html = urllib2.urlopen(url).read().encode('ascii','ignore')
    page = requests.get(url).text
    soup = BeautifulSoup(page, "lxml")
    return soup

# get links of a term as string type
def getTermLinks( letter ):
    termLinks = list()
    baseUrl = ('http://www.investopedia.com/terms/' + letter + '/')
    soup = getSoup(baseUrl)
    
    # iterate each pages and store termLink into the list
    lastPage = soup.find("a", title="Go to last page")
    if lastPage == None:
        pageCount = 1
    else:
        pageCount = int(lastPage.get("href").lstrip("terms/" + letter + "?page="))

    for pageNum in xrange(1,pageCount+1):
        if pageNum != 1:
            #(e.g)http://www.investopedia.com/terms/a/?page=13 for term 'A'
            pageUrl = ('http://www.investopedia.com/terms/' + letter + '/?page=' + str(pageNum))
            soup = getSoup(pageUrl)
            # print("url: %s") % (pageUrl)
        
        # links stores relative term url (e.g) "term/a/abend.asp"
        links = soup.find("div", class_="box col-2 big-item-title clear").find_all("a")
        
        for link in links:
            termLinks.append(link.get("href"))

    print "%s '%d' links fetched." % (baseUrl, len(termLinks))
    
    global fetchedCount
    with lock:
    	fetchedCount += len(termLinks)

    dictionary.append(termLinks)

def extractContent(idx):
 	for termLink in dictionary[idx]:

		termUrl = baseUrl + termLink
		# termUrl = "http://www.investopedia.com/terms/w/workers-compensation.asp"
		
		print termUrl

		# write on a txt file
		filePath = outDir + termUrl[len(baseUrl)+1:].rstrip(".asp") + ".txt"
		anchorFilePath = filePath.rstrip(".txt") + "_IL.txt"
		linkFilePath = filePath.rstrip(".txt") + "_RT.txt"

		targetDir = os.path.dirname(filePath)
		if not os.path.exists(targetDir):
		    os.makedirs(targetDir)

		f = codecs.open(filePath, encoding='utf-8', mode='w')
		al = codecs.open(anchorFilePath, encoding='utf-8', mode='w')
		fl = codecs.open(linkFilePath, encoding='utf-8', mode='w')

		 # extract definition and break down of term
		soup = getSoup(termUrl)

		content = soup.find("div", class_="content-box content-box-term")

		if content == None:
			logf.write(str('[Invalid Format#1!]' + termLink + '\n'))
			f.close()
			al.close()
			fl.close()
			continue

		tags = content.find_all(['h2','p'])
		hIdx = 0  # head index
		pIdx = 0  # paragraph index
		pCharCounts = 0  # counts of characters in a paragraph
		for tag in tags:

			if len(tags) <= 1:
				logf.write(str('[Invalid Format#2!]' + termLink + '\n'))
				with lock:
					global warnCount
					warnCount += 1

			if tag.name == 'h2':
				pIdx = 0
				hIdx += 1
				f.write('\n[' + tag.text + ']\n' )
			if tag.name == 'p':
				pIdx += 1
				pCharCounts = len(tag.text)
				f.write(tag.text)
				f.write('counts:%d\n' % pCharCounts )
				anchors = tag.find_all('a')
				for anchor in anchors:
					idxStart = tag.text.find(anchor.text)
					al.write('[head#%d:para#%d(%d)]' % (hIdx, pIdx, pCharCounts) )
					al.write(anchor.text + ' ' + unicode(anchor.get("href")) + ' ' + str(idxStart) + '\n')

		
		# extract related links
		relatedLinks = soup.find("div", class_="box below-box col-2 no-image gray clear").find_all("a")
		for relatedLink in relatedLinks:
		    fl.write(relatedLink.get("href") + '\n')

		with lock:
			global totalCount
			totalCount += len(termLink)

		f.close()
		al.close()
		fl.close()
			
def worker():
	    while True:
	        letter = q.get()
	        getTermLinks(letter)
	        q.task_done()

def worker2():
    while True:
        index = q2.get()
        extractContent(index)
        q2.task_done()


# -----------------------------------------------------------------------------------
# ---------------- main
# -----------------------------------------------------------------------------------
q = Queue.Queue()
q2 = Queue.Queue()
num_worker_threads = 26
logf = codecs.open(outDir + 'log.txt', encoding='utf-8', mode='a')

for i in range(num_worker_threads):
     t = threading.Thread(target=worker)
     t.daemon = True
     t.start()

for letter in letterList:
    q.put(letter)

q.join() 
print "all links are fetched.\n"

for i in range(num_worker_threads):
	t = threading.Thread(target=worker2)
	t.demon = True
	t.start()

for i in xrange(len(dictionary)):
	q2.put(i)

q2.join()

# print out result
print "\n# of fetched Pages: %d" % fetchedCount
print "# of Witten Pages: %d" % totalCount
print "# of Warnnings: %d\n\n" % warnCount

# write result data
logf.write("--------------------------------------------------------------------\n")
logf.write(str(datetime.now())+'\n')
logf.write("\n# of fetched Pages: %d" % fetchedCount)
logf.write("\n# of Witten Pages: %d" % totalCount)
logf.write("\n# of Warnnings: %d\n\n" % warnCount)
logf.close()