# -*- coding: utf-8 -*-
'''
    script.screensaver.football.panel - A Football Panel for Kodi
    RSS Feeds, Livescores and League tables as a screensaver or
    program addon 
    Copyright (C) 2016 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import xbmcgui
import xbmc
import sys
import thesportsdb
import random
import threading
import feedparser
import pytz
import datetime
from resources.lib import ignoreleagues
from resources.lib import ssutils
from resources.lib.common_addon import *

api = thesportsdb.Api("7723457519235")

class Main(xbmcgui.WindowXMLDialog):

	class ExitMonitor(xbmc.Monitor):

		def __init__(self, exit_callback):
			self.exit_callback = exit_callback

		def onAbortRequested(self):
			self.exit_callback()

		def onScreensaverDeactivated(self):
			self.exit_callback()
	
	def __init__( self, *args, **kwargs ):
		self.exit_monitor = self.ExitMonitor(self.stopRunning)
		if os.path.exists(ignored_league_list_file):
			self.ignored_leagues = eval(ssutils.read_file(ignored_league_list_file))
		else:
			self.ignored_leagues = []

	def onInit(self):
		xbmc.log(msg="[Football Panel] Script started", level=xbmc.LOGDEBUG)
		self.isRunning = True
		xbmc.executebuiltin("ClearProperty(no-games,Home)")
		xbmc.executebuiltin("ClearProperty(has-tables,Home)")
		xbmc.executebuiltin("ClearProperty(has-rss,Home)")
		xbmc.executebuiltin("SetProperty(loading,1,home)")
		
		t1 = threading.Thread(target=self.livescoresThread)
		t2 = threading.Thread(target=self.tablesThread)
		t3 = threading.Thread(target=self.rssThread)
		t1.start()
		t2.start()
		t3.start()
		t1.join()
		t2.join()
		t3.join()
		i = 0
		while self.isRunning:
			if (float(i*200)/(livescores_update_time*60*1000)).is_integer() and ((i*200)/(3*60*1000)) != 0:
				self.livescoresThread()
			if (float(i*200)/(tables_update_time*60*1000)).is_integer() and ((i*200)/(8*60*1000)) != 0:
				self.tablesThread()
			if (float(i*200)/(rss_update_time*60*1000)).is_integer() and ((i*200)/(10*60*1000)) != 0:
				self.rssThread()
			xbmc.sleep(200)
			i += 1
		xbmc.log(msg="[Football Panel] Script stopped", level=xbmc.LOGDEBUG)

	def livescoresThread(self):
		self.getLivescores()
		self.setLivescores()
		return

	def tablesThread(self):
		self.getLeagueTable()
		return

	def rssThread(self):
		self.setRss()
		return

	def setRss(self):
		feed = feedparser.parse(addon.getSetting("rss-url"))
		rss_line = ''
		for entry in feed['entries']:
			rss_line = rss_line + entry['summary_detail']['value'] + "|"
		if rss_line:
			self.getControl(RSS_FEEDS).setLabel("")
			self.getControl(RSS_FEEDS).setLabel(rss_line)
			xbmc.executebuiltin("ClearProperty(loading,Home)")
			xbmc.executebuiltin("SetProperty(has-rss,1,home)")

	def getLivescores(self):
		self.livescoresdata = api.Livescores().Soccer(objects=True)
		return

	def set_no_games(self):
		images = []
		league_id = ssutils.get_league_id_no_games()
		teams = api.Lookups().Team(leagueid=league_id)
		for team in teams:
			if team.strTeamFanart3: images.append(team.strTeamFanart3)
			if team.strTeamFanart4: images.append(team.strTeamFanart4)
		
		if images:
			random_photo = images[random.randint(0,len(images)-1)]
			self.getControl(NO_GAMES).setImage(random_photo)
		xbmc.executebuiltin("ClearProperty(loading,Home)")
		xbmc.executebuiltin("SetProperty(no-games,1,home)")
		return

	def getLeagueTable(self):
		self.table = []
		tables = ssutils.get_league_tables_ids()
		table_id = random.randint(0,len(tables)-1)
		league = api.Lookups().League(tables[table_id])[0]
		table = api.Lookups().Table(tables[table_id],objects=True)
		
		for tableentry in table:
			try:
				if show_alternative == "false":
					item = xbmcgui.ListItem(tableentry.name)
				else:
					item = xbmcgui.ListItem(tableentry.Team.AlternativeNameFirst)
				item.setArt({ 'thumb': tableentry.Team.strTeamBadge })
				item.setProperty('points',str(tableentry.total))
				self.table.append(item)
			except:pass
		
		self.getControl(LEAGUETABLES_LIST_CONTROL).reset()
		if league.strLogo:
			self.getControl(LEAGUETABLES_CLEARART).setImage(league.strLogo)
		self.getControl(LEAGUETABLES_LIST_CONTROL).addItems(self.table)
		xbmc.executebuiltin("ClearProperty(loading,Home)")
		xbmc.executebuiltin("SetProperty(has-tables,1,home)")
		return
		
	def setLivescores(self):
		items = []
		if self.livescoresdata:
			for livegame in self.livescoresdata:
				if removeNonAscii(livegame.League) not in str(self.ignored_leagues):
					#decide to add the match or not
					if (livegame.Time.lower() != "not started") and (livegame.Time.lower() != "finished"):
						add = True
					else:
						if livegame.Time.lower() == "not started" and hide_notstarted == "true":
							add = False
						elif livegame.Time.lower() == "finished" and hide_finished == "true":
							add = False
						else:
							add = True
						
					if add == True:
						item = xbmcgui.ListItem(livegame.HomeTeam+livegame.AwayTeam)
						item.setProperty('result',str(livegame.HomeGoals)+"-"+str(livegame.AwayGoals))
						item.setProperty('home_team_logo',livegame.HomeTeamObj.strTeamBadge)
						item.setProperty('away_team_logo',livegame.AwayTeamObj.strTeamBadge)
						if bool(int(livegame.HomeGoals)>0):
							item.setProperty('has_home_goals',"goal.png")
						if bool(int(livegame.AwayGoals)>0):
							item.setProperty('has_away_goals',"goal.png")
						if livegame.HomeGoalDetails: item.setProperty('home_goal_details',livegame.HomeGoalDetails)
						if livegame.AwayGoalDetails: item.setProperty('away_goal_details',livegame.AwayGoalDetails)
						item.setProperty('league_and_round',livegame.League+' - Round '+livegame.Round)
						
						#red cards
						if livegame.HomeTeamRedCardDetails:
							home_redcards = livegame.HomeTeamRedCardDetails.split(";")
							if len(home_redcards) == 1: item.setProperty('home_redcard1',"redcard.png")
							elif len(home_redcards) > 1:
								item.setProperty('home_redcard1',"redcard.png")
								item.setProperty('home_redcard2',"redcard.png")
						if livegame.AwayTeamRedCardDetails:
							away_redcards = livegame.AwayTeamRedCardDetails.split(";")
							if len(away_redcards) == 1: item.setProperty('away_redcard1',"redcard.png")
							elif len(away_redcards) > 1:
								item.setProperty('away_redcard1',"redcard.png")
								item.setProperty('away_redcard2',"redcard.png")
						
						#Convert event time to user timezone
						if livegame.Time.lower() == "not started":
							try:
								db_time = pytz.timezone(str(pytz.timezone("Europe/London"))).localize(livegame.DateTime)
								my_location=pytz.timezone(pytz.all_timezones[int(my_timezone)])
								converted_time=db_time.astimezone(my_location)
								starttime=converted_time.strftime("%H:%M")
								item.setProperty('starttime',starttime)
							except: pass

						#check match status
						item.setProperty('minute',str(livegame.Time))
						if livegame.Time.lower() == "finished": status = "redstatus.png"
						elif "'" in livegame.Time.lower(): status = "greenstatus.png"
						else: status = "yellowstatus.png"
						item.setProperty('status',status)
						items.append(item)

		self.getControl(LIVESCORES_PANEL_CONTROL_1).reset()
		self.getControl(LIVESCORES_PANEL_CONTROL_2).reset()
		if items:
			xbmc.executebuiltin("ClearProperty(loading,Home)")
			xbmc.executebuiltin("ClearProperty(no-games,Home)")
			if len(items) < 3:
				self.getControl(LIVESCORES_PANEL_CONTROL_1).addItems(items)
			else:
				self.getControl(LIVESCORES_PANEL_CONTROL_1).addItems(items[0:int(round(len(items)/2))])
				self.getControl(LIVESCORES_PANEL_CONTROL_2).addItems(items[int(round(len(items)/2))+1:])
		else:
			self.set_no_games()
		return

	def stopRunning(self):
		self.isRunning = False
		self.close()

	def onAction(self,action):
		if action.getId() == 92 or action.getId() == 10:
			self.stopRunning()


if not sys.argv[0]:
	main = Main(
			'script-livescores-Main.xml',
			addon_path,
			'default',
			'',
			)
	main.doModal()
	del main

else:
	ignoreWindow = ignoreleagues.Select(
			'DialogSelect.xml',
			addon_path,
			'default',
			'',
			)
	ignoreWindow.doModal()
	del ignoreWindow