#!/usr/bin/env python

import os
import webapp2
import re
import jinja2
import random
import string
import hashlib
import hmac
import json
import logging
import time

from google.appengine.api import memcache
from models import *

template_dir = os.path.join(os.path.dirname(__file__), '../templates')
jinja_env= jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

SECRET = 'imsosecret'

# --------------------------------------
# FUNCTIONS (FROM CLASS)
# --------------------------------------

# replaces first celement in each tupe with the second to escape said character
def escape_html(s):
    for (i, o) in (("&", "&amp;"),
                   ("<", "&lt;"),
                   (">", "&gt;"),
                   ('"', "&quot;")):
        s = s.replace(i, o)
    return s

def get_user(self):
    user_id = -1
    user_id_str = self.request.cookies.get('user_id')
    if user_id_str:
        cookie_val = check_secure_val(user_id_str)
        if cookie_val:
            user_id = int(cookie_val)
            if user_id != -1:
                user = User.get_by_id(int(user_id))
                if user:
                    return user
    return None

# Cookie Hash Functions

# hashes string s with secret key
def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()

# uses this hash to make secure: cannot be guessed
def make_secure_val(s):
    return "%s|%s" % (s, hash_str(s))

# makes sure cookie = hash value
def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val

# --------------------------------------
# HANDLERS (FROM CLASS)
# --------------------------------------

# this class saves us having to write self.response.out.write (instead we can just use the 'render' function, with any number of args)
class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


# wiki front page handler: dispalys titles of all wiki posts retrieved from the database
class WikiHandler(Handler):
    def get(self):
        user = get_user(self)
        wikis = db.GqlQuery("SELECT * FROM WikiPage where version=1 ORDER BY title DESC") #querys db to get all posts
        wikis = list(wikis)
        
        if user: # ie if valid user
            self.render("wiki.html", wikis=wikis, user=user) # for logged in  user: dispalys user name
        else:
            self.render("wiki.html", wikis=wikis) # when not logged in; can't edit
    

# governs the editing of a wiki post or the creation of a new one
class EditPageHandler(Handler):
    def render_editwiki(self, user="", title="", content="", error=""):
        self.render("editwiki.html", user=user, title=title, content=content, error=error) # renders our edit page template with args plugged into jinja template
    
    def get(self, title):
        user = get_user(self)
        v = self.request.get('v') # v is the version of a post; allows for history
        
        if user:
            if v: # if there is more than one version
                v = int(v) # converts get parameter string into an int
                wiki_valid = db.GqlQuery("SELECT * FROM WikiPage WHERE title = :1 AND version = :2 ORDER BY created DESC", title, v).get() # gets relevant title and version number to edit
                if not wiki_valid:
                    self.redirect("/wiki/_edit%s" % title)
            else: # if this is our first version
                wiki_valid = db.GqlQuery("SELECT * FROM WikiPage WHERE title = :1 ORDER BY created DESC LIMIT 1", title).get()
                if not wiki_valid: # if empty contents
                    self.render_editwiki(user, title)
            
            if wiki_valid:
                id = wiki_valid.key().id()
                wiki_page = WikiPage.get_by_id(int(id)) # gets relevant post to edit from db
                self.render_editwiki(user, wiki_page.title, wiki_page.content) # renders edit page with all valid data
        else:
            self.redirect("/wiki/signup") # if not logged in or not a valid user
        
    def post(self, title):
        content = self.request.get("content") # data entered into textbox
        user = get_user(self) # gets user from cookie
                        
        if user: # if logged in and valid user
            if title and content:
                wiki_valid = db.GqlQuery("SELECT * FROM WikiPage where title = :1 ORDER BY created DESC LIMIT 1", title).get()
                if wiki_valid: # id we have created this wiki post yet
                    id = wiki_valid.key().id()
                    prev_wiki_page = WikiPage.get_by_id(int(id))
                    cur_version = prev_wiki_page.version + 1 # creates a new version
                    wiki_page = WikiPage(title=title, content=content, version=cur_version)
                    wiki_page.put() # puts this new edit into db
                else: # ie if we are creating this post for the first time
                    wiki_page = WikiPage(title=title, content=content, version=1)
                    wiki_page.put() # saves to db

                self.redirect("/wiki%s" % wiki_page.title) # after editng, redirects to new version we just created
            else: # if no data entered into text box, message below is printed
                error = "content needed!"
                self.render_editwiki(user, title, content, error) # renders again with error message, giving us another try
        else:
            self.redirect("/wiki/signup") # if not logged in or not a valid user

 
 # governs behavior of page showing all versions of a wiki post   
class HistoryPageHandler(Handler):
    def get(self, title):
        user = get_user(self)
        if user: # if valiud user and logged in 
            wikis = db.GqlQuery("SELECT * FROM WikiPage WHERE title = :1 ORDER BY created DESC", title) # gets all versions of this particular post
            if wikis: # if we get anything
                wikis = list(wikis)
                self.render("wikihistory.html", wikis=wikis, user=user) # renders history page template with all version passed into jinja for rendering
            else: 
                self.redirect("/wiki/_edit%s" % title)
        else: # if not logged in or invalid user
            self.redirect("/wiki/signup")
        

# governs behavior of main page for a particular wiki post
class WikiPageHandler(Handler):
    def get(self, title):
        wiki_valid = None
        v = self.request.get('v') # gets version number
        
        if v: # if we have a version number
            v = int(v) # converts string to int
            wiki_valid = db.GqlQuery("SELECT * FROM WikiPage WHERE title = :1 AND version = :2 ORDER BY created DESC", title, v).get() # gets relevant version number from db
            if not wiki_valid: # simply redirects to main page for that wiki post title if we don't get a version number
                self.redirect("/wiki%s" % title)
        else:
            wiki_valid = db.GqlQuery("SELECT * FROM WikiPage WHERE title = :1 ORDER BY created DESC LIMIT 1", title).get()
            if not wiki_valid: # ie if not created yet
                self.redirect("/wiki/_edit%s" % title)
                
        if wiki_valid:
            id = wiki_valid.key().id()
            wiki_page = WikiPage.get_by_id(int(id))
            user = get_user(self)
            if user:
                self.render("wikipage.html", wiki_page=wiki_page, user=user) # if all goes well, we redirect to the page for an individual post with correct version number, with user logged in
            else:
                self.render("wikipage.html", wiki_page=wiki_page)
            
    