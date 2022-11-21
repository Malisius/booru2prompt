# booru2prompt // Turn booru posts into Stable Diffusion prompts!

This is an extension for [stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui).

### If you like this project, I encourage you to fork it and help me work on it! If you *really* like this project, please hire me to write more python for you. Just don't ask me to do any more javascript.

This SD extension allows you to turn posts from various image boorus into stable diffusion prompts. It does so by pulling a list of tags down from their API. You can copy-paste in a link to the post you want yourself, or use the built-in search feature to do it all without leaving SD.

To install this extension, navigate to your `extensions` directory and run `git clone https://github.com/Malisius/booru2prompt.git`. You can either restart SD completely or look at the bottom of SD's settings for `Restart Gradio and Refresh Components`. 

To start, visit the `API Keys` tab to put in your API keys. Most features should work without this, but some things like sort tags might not work depending on the restrictions of the booru.
The included `settings.json` has configuration for danbooru.donmai.us and aibooru.space, but you can add your own by following the same format. Just add a new entry to the `boorus` list with the `name` and `host` keys.

`{"name": "Danbooru", "host": "https://danbooru.donmai.us", "username": "", "apikey": ""}`

Take note: calls to aibooru.space are returning `403: Forbidden` no matter what I try. Any help with that would be appreciated.  
  
![image](https://user-images.githubusercontent.com/6227122/202934555-5eb73c22-aa8c-4757-b122-c47e6b7e7964.png)

Once that's set, visit the `Select` tab pull down a post. You can paste in a link to the post in the `Link to image page` field, then hit `Select Image` at the bottom.  
  
![image](https://user-images.githubusercontent.com/6227122/202934902-a990e190-cb51-451c-89ba-0c61c7ac3cf4.png)
  
- Take note of the `Current Booru` at the top. The API call will be made with the credentials for that booru, so make sure it matches the link to the post you're selecting.
- Don't worry about url parameters in your link. They'll be removed automatically by the extension.
- As an alternative, you can select a post with the format `id:xxxxxx`. In the above axample, this would be `id:5298308`. This is the format used by the search feature.
- You can select which extra tags to include in the final tag string with the checkboxes. If you change any of these, you'll have to hit `Select Image` again to change the final string.
- There are options to modify the resulting prompt by adding commas and removing underscores. I'm not yet certain how much of an effect these have on generated images. I suspect it may have a lot to do with how your model was trained. Personally, I get different results by changing these, but it's hard to say which way is better. Use your discretion.
  
Once your image is loaded and you're happy with the tag string, use one of the buttons at the bottom to send it where you want to go.  
  
  ![image](https://user-images.githubusercontent.com/6227122/202936317-c1d6741a-d6e3-43de-8d83-c6ca78ea92f2.png)
  
---
  
(txt2img results from the above prompt, with no cherry picking, no negative prompt, and no other modifications to the prompt)
![grid-0041](https://user-images.githubusercontent.com/6227122/202936978-4850e02c-cf41-4a23-a0ba-cf33fc78b0e8.png)  

---
   
You can also search for images right in the extension! Just visit the `Search` tab.  
Enter in your search exactly as you would on an image booru: a list of tags seperated by spaces. These are sent to the API the same way a normal search is, so qualifier tags like `order:` and `rating:` should all work, assuming the image booru you're searching supports them.  
By default, results with the `animated` tag will be automatically excluded. There's really no reason to turn that off right now, since I haven't yet figured out how to put anything other than a static image in a Gradio gallery.  
  
![image](https://user-images.githubusercontent.com/6227122/202935945-73aee137-e788-4588-947a-96c84f76cd6e.png)
  
Having done that, just hit `Send image to tag selection` to continue.  
  
---
This was a lot of fun to make, so if you have any feedback, please let me know! I plan on updating this frequently with some more ideas I have. What I really want is a browser extension to add a button directly to an image booru website to send a post right over to SD. Perhaps one day.
