#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import webapp2
import jinja2

template_dir = os.path.join(os.path.dirname(__file__), '../templates')
jinja_env= jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

def escape_html(s):
    for (i, o) in (("&", "&amp;"),
                   ("<", "&lt;"),
                   (">", "&gt;"),
                   ('"', "&quot;")):
        s = s.replace(i, o)
    return s

def rot13(input):
    chars = "abcdefghijklmnopqrstuvwxyz"
    caps = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    output = ""
    for i in range(0, len(input)):
        if input[i] in chars:
            ind = (chars.index(input[i]) + 13) % 26
            output = output + chars[ind]
        elif input[i] in caps:
            ind = (caps.index(input[i]) + 13) % 26
            output = output + caps[ind]
        else:
            output = output + input[i]
    return output

class Rot13Handler(Handler):
    def render_rot13(self, text=""):
        self.render("rot.html", text=text)
    
    def get(self):
        self.render_rot13()
    
    def post(self):
        text = rot13(self.request.get('text'))
        self.render_rot13(escape_html(text))
