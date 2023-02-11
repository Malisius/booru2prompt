import json
import os
from urllib.request import urlopen, urlretrieve, Request
from urllib import parse
import inspect

import gradio as gr

import modules.ui
from modules import script_callbacks, scripts

#The auto1111 guide on developing extensions says to use scripts.basedir() to get the current directory
#However, for some reason, this kept returning the stable diffusion root instead.
#So this is my janky workaround to get this extensions directory.
edirectory = inspect.getfile(lambda: None)
edirectory = edirectory[:edirectory.find("scripts")]

def loadsettings():
    """Return a dictionary of settings read from settings.json in the extension directory

    Returns:
        dict: settings and api keys
    """    
    print("Loading booru2prompt settings")
    file = open(edirectory + "settings.json")
    settings = json.load(file)
    file.close()
    return settings

def savesettings(active, username, apikey, negprompt):
    """Save the current username and api key to the active booru

    Args:
        active (str): The string identifier of the currently selected booru
        username (str): The username for that booru
        apikey (str): The user's api key
        negprompt (str): The negative prompt to be appended to each image selection
    """    
    settings["active"] = active
    settings["negativeprompt"] = negprompt

    #Stepping through all the boorus in the settings till we find the right one
    for booru in settings['boorus']:
        if booru['name'] == active:
            booru["username"] = username
            booru["apikey"] = apikey
    file = open(edirectory + "settings.json", "w")
    file.write(json.dumps(settings))
    file.close()

#We're loading the settings here since all the further functions depend on this existing already
settings = loadsettings()

def getauth():
    """Get the username and api key for the currently selected booru

    Returns:
        tuple: (username, apikey) for whichever booru is selected in the dropdown
    """    
    for b in settings['boorus']:
        if b['name'] == settings['active']:
            return b['username'], b['apikey']

def gethost():
    """Get the url for the currently selected booru.
    This url will get piped straight into every request, so https:// should be
    included in each in settings.json if you want to use ssl.
    Furthermore, you should include a trailing slash in these urls, since they're already
    added by every other function here that uses this function.

    Returns:
        str: The full url for the selected booru
    """    
    for booru in settings['boorus']:
        if booru['name'] == settings['active']:
            return booru['host']

def searchbooru(query, removeanimated, curpage, pagechange=0):
    """Search the currently selected booru, and return a list of images and the current page.

    Args:
        query (str): A list of tags to search for, delimited by spaces
        removeanimated (bool): True to append -animated to searches
        curpage (str or int): The current page to search
        pagechange (int, optional): How much to change the current page by before searching. Defaults to 0.

    Returns:
        tuple (list, str): The list in this tuple is a list of tuples, where [0] is
        a str filepath to a locally saved image, and [1] is a string representation
        of the id for that image on the searched booru.
        The string in this return is new current page number, which may or may not have been changed.
    """    
    host = gethost()
    u, a = getauth()

    #If the page isn't changing, then the user almost certainly is initiating a new
    #search, so we can set the page number back to 1.
    if pagechange == 0:
        curpage = 1
    else:    
        curpage = int(curpage) + pagechange
        if curpage < 1:
            curpage = 1

    #We're about to use this in a url, so make it a string real quick
    curpage = str(curpage)

    url = host + f"/posts.json?"

    #Only append login parameters if we actually got some from the above getauth()
    #In the default settings.json in the repo, these are empty strings, so they'll
    #return false here.
    if u:
        url += f"login={u}&"
    if a:
        url += f"api_key={a}&"

    #Prepare the append some search tags
    #We can leave this here even if param:query is empty, since the api call still works apparently
    url += "tags="

    #Add in the -animated tag if that checkbox was selected
    #I have no idea what happens if "animated" is searched for and that box is checked,
    #and I'm not testing that myself
    if removeanimated:
        url += "-animated+"

    #TODO: Add a settings option to change the images-per-page here
    url += f"{parse.quote_plus(query)}&limit=6"
    url += f"&page={curpage}"

    #I had this print here just to test my url building, but I kind of like it, so I'm leaving it
    print(url)

    #Normally it's fine to call urlopen() with just a string url, but some boorus get finicky about
    #setting a user-agent, so this builds a request with custom headers
    request = Request(url, data=None, headers = {'User-Agent': 'booru2prompt, a Stable Diffusion project (made by Borderless)'})
    response = urlopen(request)
    data = json.loads(response.read())

    localimages = []

    #Creating the required directory for temporary images could be done in a preload.py, but I prefer to do this
    #check each time we go to save images, just in case
    if not os.path.exists(edirectory + "tempimages"):
        os.makedirs(edirectory + "tempimages")

    #The length of the returned json array might not actually be equal to what we reqeusted with limit=,
    #so we need to make sure to only step through what we got back
    for i in range(len(data)):
        #So I guess not every returned result has a 'file_url'. Could not tell you why that is.
        #Doesn't matter. If there's no file to grab, just skip the entry.
        if 'file_url' in data[i]:
            imageurl = data[i]['file_url']
            #The format of this string is important. When we later go to query for specific posts, the user can use
            #"id:xxxxxx" instead of a full url to make that request
            id = "id:" + str(data[i]['id'])
            #I forget why I added this
            if "http" not in imageurl:
                imageurl = gethost() + imageurl
            #We're storing the images locally to be crammed into a Gradio gallery later.
            #This seemed simpler than using PIL images or whatever.
            savepath = edirectory + f"tempimages\\temp{i}.jpg"
            image = urlretrieve(imageurl, savepath)
            localimages.append((savepath, id))

    #We're returning not just the images for the gallery, but the current page number
    #So that textbox in Gradio can be updated
    return localimages, curpage

def gotonextpage(query, removeanimated, curpage):
    return searchbooru(query, removeanimated, curpage, pagechange=1)

def gotoprevpage(query, removeanimated, curpage):
    return searchbooru(query, removeanimated, curpage, pagechange=-1)

def updatesettings(active = settings['active']):
    """Update the relevant textboxes in Gradio with the appropriate data when
    the user selects a new booru in the dropdown

    Args:
        active (str, optional): The str name of the booru the user switched to. Defaults to settings['active'].

    Returns:
        (str, str, str, str): The username, apikey, name, and name again of the selected booru.
        We're only returning the name twice here since it needs to update two seperate Gradio components.
    """    
    settings['active'] = active
    for booru in settings['boorus']:
        if booru['name'] == active:
            username = booru['username']
            apikey = booru['apikey']
    return username, apikey, active, active

def grabtags(url, negprompt, replacespaces, replaceunderscores, escapeparentheses, includeartist, includecharacter, includecopyright, includemeta):
    """Get the tags for the selected post and update all the relevant textboxes on the Select tab.

    Args:
        url (str): Either the full path to the post, or just the posts' id, formatted like "id:xxxxxx"
        negprompt (str): A negative prompt to paste into the relevant field. Setting to None will delete the existing negative prompt at the target
        replacespaces (bool): True to replace all the spaces in the tag list with ", "
        replaceunderscores (bool): True to replace the underscores in each tag with a space
        escapeparentheses (bool): True to escape the parentheses in each tag
        includeartist (bool): True to include the artist tags in the final tag string
        includecharacter (bool): True to include the character tags in the final tag string
        includecopyright (bool): True to include the copyright tags in the final tag string
        includemeta (bool): True to include the meta tags in the final tags string

    Returns:
        (str, str, str, str, str, str): A bunch of strings that will update some gradio components.
        In order, it's the final tag string, the local path to the saved image, the artist tags, the
        character tags, the copyright tags, and the meta tags.
    """
    #This check may be uneccesary, but we should fail out immediately if the url isn't a string.
    #I struggle to remember what circumstance compelled me to add this.
    if not isinstance(url, str):
        return

    #Quick check to see if the user is selecting with the "id:xxxxxx" format.
    #If the are, we can all the extra stuff for them
    if url[0:2] == "id":
        url = gethost() + "/posts/" + url[3:]

    #Many times, copying a link right off the booru will result in a lot of extra
    #url parameters. We need to get rid of all those before we add our own.
    index = url.find("?")
    if index > -1:
        url = url[:index]

    #Check to make sure the request isn't already a .json api call before we add it ourselves
    if not url[-4:] == "json":
        url = url + ".json"

    #Add the question mark denoting url parameters back in
    url += "?"

    u, a = getauth()

    #Only append login parameters if we actually got some from the above getauth()
    #In the default settings.json in the repo, these are empty strings, so they'll
    #return false here.
    if u:
        url += f"login={u}&"
    if a:
        url += f"api_key={a}&"

    print(url)

    response = urlopen(url)
    data = json.loads(response.read())

    tags = data['tag_string_general']
    imageurl = data['file_url']

    if "http" not in imageurl:
        imageurl = gethost() + imageurl

    artisttags = data["tag_string_artist"]
    charactertags = data["tag_string_character"]
    copyrighttags = data["tag_string_copyright"]
    metatags = data["tag_string_meta"]

    #We got all these extra tags, but we're only including them in the final string if the relevant 
    #checkboxes have been checked
    if includeartist and artisttags:
        tags = artisttags + " " + tags
    if includecharacter and charactertags:
        tags = charactertags + " " + tags
    if includecopyright and copyrighttags:
        tags = copyrighttags + " " + tags
    if includemeta and metatags:
        tags = metatags + " " + tags

    #It would be a shame if someone got these backwards and couldn't figure out the issue for a whole day
    if replacespaces:
        tags = tags.replace(" ", ", ")
    if replaceunderscores:
        tags = tags.replace("_", " ")
    if escapeparentheses:
        tags = tags.replace("(", "\\(").replace(")", "\\)")

    #Adding a line for the negative prompt if we receieved one
    #It's formatted this way very specifically. This is how the metadata looks on pngs coming out of SD
    if negprompt:
        tags += f"\nNegative prompt: {negprompt}"

    #Creating the temp directory if it doesn't already exist
    if not os.path.exists(edirectory + "tempimages"):
        os.makedirs(edirectory + "tempimages")
    urlretrieve(imageurl, edirectory +  "tempimages\\temp.jpg")

    #My god look at that tuple
    return (tags, edirectory + "tempimages\\temp.jpg", artisttags, charactertags, copyrighttags, metatags)

def on_ui_tabs():
    #Just setting up some gradio components way early
    #For the most part, I've created each component at the place where it will be rendered
    #However, for these ones, I need to reference them before they would've otherwise been
    #initialized, so I put them up here instead. This is totally fine, since they can be 
    #rendered in the appropirate place with .render()
    boorulist = [booru["name"] for booru in settings["boorus"]]
    selectimage = gr.Image(label="Image", type="filepath", interactive=False)
    searchimages = gr.Gallery(label="Search Results")
    searchimages.style(grid=3)
    activeboorutext1 = gr.Textbox(label="Current Booru", value=settings['active'], interactive=False)
    activeboorutext2 = gr.Textbox(label="Current Booru", value=settings['active'], interactive=False)
    curpage = gr.Textbox(value="1", label="Page Number", interactive=False, show_label=True)
    negprompt = gr.Textbox(label="Negative Prompt", value=settings['negativeprompt'], placeholder="Negative prompt to send with along with each prompt")

    with gr.Blocks() as interface:
        with gr.Tab("Select"):
            with gr.Row(equal_height=True):
                with gr.Column():
                    activeboorutext1.render()
                    #Go to that link, I dare you
                    imagelink = gr.Textbox(label="Link to image page", elem_id="selectbox", placeholder="https://danbooru.donmai.us/posts/4861569 or id:4861569")

                    with gr.Row():
                        selectedtags_artist = gr.Textbox(label="Artist Tags", interactive=False)
                        includeartist = gr.Checkbox(value=True, label="Include artist tags in tag string", interactive=True)
                    with gr.Row():
                        selectedtags_character = gr.Textbox(label="Character Tags", interactive=False)
                        includecharacter = gr.Checkbox(value=True, label="Include character tags in tag string", interactive=True)
                    with gr.Row():
                        selectedtags_copyright = gr.Textbox(label="Copyright Tags", interactive=False)
                        includecopyright = gr.Checkbox(value=True, label="Include copyright tags in tag string", interactive=True)
                    with gr.Row():
                        selectedtags_meta = gr.Textbox(label="Meta Tags", interactive=False)
                        includemeta = gr.Checkbox(value=False, label="Include meta tags in tag string", interactive=True)

                    selectedtags = gr.Textbox(label="Image Tags", interactive=False, lines=3)

                    replacespaces = gr.Checkbox(value=True, label="Replace spaces with a comma and a space", interactive=True)
                    replaceunderscores = gr.Checkbox(value=False, label="Replace underscores with spaces")
                    escapeparentheses = gr.Checkbox(value=True, label="Escape parentheses")

                    selectbutton = gr.Button(value="Select Image", variant="primary")
                    selectbutton.click(fn=grabtags,
                        inputs=
                            [imagelink, 
                            negprompt,
                            replacespaces, 
                            replaceunderscores,
                            escapeparentheses,
                            includeartist, 
                            includecharacter, 
                            includecopyright, 
                            includemeta], 
                        outputs=
                            [selectedtags, 
                            selectimage, 
                            selectedtags_artist, 
                            selectedtags_character, 
                            selectedtags_copyright, 
                            selectedtags_meta])

                    clearselected = gr.Button(value="Clear")
                    #This is just a cheeky way to clear out all the components in this tab. I'm sure this is not what you're meant to use lambda functions for.
                    clearselected.click(fn=lambda: (None, None, None, None, None, None, None), outputs=[selectimage, selectedtags, selectedtags_artist, selectedtags_character, selectedtags_copyright, selectedtags_meta, imagelink])
                with gr.Column():
                    selectimage.render()
                    with gr.Row(equal_height=True):
                        #Don't even ask me how this works. I spent like three days reading generation_parameters_copypaste.py
                        #and I still don't quite know. Automatic1111 must've been high when he wrote that.
                        sendselected = modules.generation_parameters_copypaste.create_buttons(["txt2img", "img2img", "inpaint", "extras"])
                        modules.generation_parameters_copypaste.bind_buttons(sendselected, selectimage, selectedtags)
        with gr.Tab("Search"):
            with gr.Row(equal_height=True):
                with gr.Column():
                    activeboorutext2.render()
                    searchtext = gr.Textbox(label="Search string", placeholder="List of tags, delimited by spaces")
                    removeanimated = gr.Checkbox(label="Remove results with the \"animated\" tag", value=True)
                    searchbutton = gr.Button(value="Search Booru", variant="primary")
                    searchtext.submit(fn=searchbooru, inputs=[searchtext, removeanimated, curpage], outputs=[searchimages, curpage])
                    searchbutton.click(fn=searchbooru, inputs=[searchtext, removeanimated, curpage], outputs=[searchimages, curpage])
                with gr.Column():
                    with gr.Row():
                        prevpage = gr.Button(value="Previous Page")
                        curpage.render()
                        nextpage = gr.Button(value="Next Page")
                        #The functions called here will then call searchbooru, just with a page in/decrement modifier
                        prevpage.click(fn=gotoprevpage, inputs=[searchtext, removeanimated, curpage], outputs=[searchimages, curpage])
                        nextpage.click(fn=gotonextpage, inputs=[searchtext, removeanimated, curpage], outputs=[searchimages, curpage])
                    searchimages.render()
                    with gr.Row():
                        sendsearched = gr.Button(value="Send image to tag selection", elem_id="sendselected")
                        #In this particular instance, the javascript function will be used to read the page, find the selected image in
                        #gallery, and send it back here to the imagelink output. I cannot fathom why Gradio galleries can't
                        #be used as inputs, but so be it.
                        sendsearched.click(fn = None, _js="switch_to_select", outputs = imagelink)
        with gr.Tab("Settings/API Keys"):
            settingshelptext = gr.HTML(interactive=False, show_label = False, value="API info may not be necessary for some boorus, but certain information or posts may fail to load without it. For example, Danbooru doesn't show certain posts in search results unless you auth as a Gold tier member.")
            settingshelptext2 = gr.HTML(interactive=False, show_label=False, value="Also, please set the booru selection here before using select or search.")
            booru = gr.Dropdown(label="Booru",value=settings['active'],choices=boorulist, interactive=True)
            u, a = getauth()
            username = gr.Textbox(label="Username", value=u)
            apikey = gr.Textbox(label="API Key", value=a)
            negprompt.render()
            savesettingsbutton = gr.Button(value="Save Settings", variant="primary")
            savesettingsbutton.click(fn=savesettings, inputs=[booru, username, apikey, negprompt])
            booru.change(fn=updatesettings, inputs=booru, outputs=[username, apikey, activeboorutext1, activeboorutext2])

    return (interface, "booru2prompt", "b2p_interface"),

script_callbacks.on_ui_tabs(on_ui_tabs)
