"""
NEO exchange: NEO observing portal for Las Cumbres Observatory
Copyright (C) 2015-2019 LCO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

from .base import FunctionalTest
from selenium import webdriver

class LayoutAndStylingTest(FunctionalTest):

    def layout_and_styling(self):
        # Eduardo goes to the homepage
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1280, 1024)

        # He notices the targets box is offset from the left edge
        link = self.browser.find_element_by_partial_link_text('active targets')
        # Magic values from masthead padding in styles.css
        self.assertGreaterEqual(link.location['x'] , 35)
