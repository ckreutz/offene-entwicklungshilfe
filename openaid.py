# -*- coding: utf-8 -*-
# all the imports
from csv import writer as csv_writer
import json
import sqlite3
from flaskext.markdown import Markdown
from flask import Flask, request, g, render_template, send_from_directory, redirect
from contextlib import closing
from random import choice

# configuration
DATABASE = 'CRS-Germany.sqlite'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

Markdown(app)

def connect_db():
	return sqlite3.connect(app.config['DATABASE'])

def init_db():
	with closing(connect_db()) as db:
		with app.open_resource('schema.sql') as f:	            
			db.cursor().executescript(f.read())
		db.commit()

def query_db(query, args=(), one=False):
	cur = g.db.execute(query, args)
	rv = [dict((cur.description[idx][0], value)
		for idx, value in enumerate(row)) for row in cur.fetchall()]
	return (rv[0] if rv else None) if one else rv

def tremapCalc(values):
	t = values
	t['show'] = "true"
	colors = ["#6b7d16","#434e7d","#5ba990","#319373","#077d56"]
	if t['treearea'] <= 7:
		t['show'] = "false"	
 	t['color'] = choice(colors)
	return t

@app.template_filter()
def number_trunc(float):
	return "%.*f" % (0, float)
	
@app.template_filter()
def number_format(value, tsep='.', dsep=','):
	s = unicode(value)
	cnt = 0
	numchars = dsep + '0123456789'
	ls = len(s)	
	while cnt < ls and s[cnt] not in numchars:
		cnt += 1
	lhs = s[:cnt]
	s = s[cnt:]
	if not dsep:
		cnt = -1
	else:
		cnt = s.rfind(dsep)
	if cnt > 0:
		rhs = dsep + s[cnt+1:]
		s = s[:cnt]
	else:
		rhs = ''
	splt = ''
	while s != '':
		splt = s[-3:] + tsep + splt
		s = s[:-3]
	return lhs + splt[:-1] + rhs

@app.before_request
def before_request():
	"""Make sure we are connected to the database each request."""
	g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
	"""Closes the database again at the end of the request."""
	if hasattr(g, 'db'):
		g.db.close()

@app.route('/')
def show_start():
       
    sektoren = query_db('select sum(usd_disbursement * 1000000) as total, sector_de from crs join sectorcode on crs.sectorcode = sectorcode.code group by sectorname order by total desc limit 10')

    gesamt = []
    for p in query_db('SELECT Year, round(sum(usd_disbursement  * 1000000)) as total_sum FROM crs where Year between 2000 and 2012 group by Year'):
        for k in query_db('SELECT Year, round(sum(usd_disbursement  * 1000000)) as red_sum FROM crs where Year between 2000 and 2012 and sectorcode is not 600 group by Year'):
            p['red_sum'] = k['red_sum']    
        gesamt.append(p)

    total = query_db('SELECT round(sum(usd_disbursement  * 1000000),2) as total, crsid, sectorname FROM crs order by total desc', one=True)
    total = total['total']

    entries = []
    for u in query_db('SELECT round(sum(usd_disbursement  * 1000000),2) as main_value, crsid, sectorname, sectorcode, count(sectorname) as activities, sectorcode.sector_de FROM crs join sectorcode on sectorcode.code = crs.sectorcode where usd_commitment > 0 group by sectorname order by main_value desc'):		
		u['treearea'] = u['main_value'] / total * 100
		u = tremapCalc(u)
		entries.append(u) 
	
    return render_template('start.html', sektoren=sektoren, gesamt=gesamt, entries=entries)  
    #return str(gesamt)

@app.route('/laender/')
def show_countries():
	info = []
	for f in query_db('SELECT land, recipient, last_year, code FROM countries where land not like "%regional" and exclude is not 0 and code < 1000 order by land'):
		info.append(f)
	return render_template('countries.html', info=info)

@app.route('/land/<country>/<year>/')
def show_recipient_year(country,year):	
    position = []
    i = 1
    for q in query_db('SELECT recipientname, recipientcode, round(sum(usd_disbursement * 1000000)) as main_value FROM crs where Year between 2000 and 2012 group by recipientname order by round(sum(usd_commitment * 1000000)) desc'):
		if q['recipientcode'] == int(country):
			""" -1 weil bilteral unspecified der größte Topf ist und so rausgenommen wird"""
			q['pole'] = i - 1
			position.append(q) 
		i+=1
	
    topsector = query_db('select sum(usd_disbursement * 1000000) as total, crs.sectorcode, sectorcode.sector_de as sectorname from crs join sectorcode on crs.sectorcode = sectorcode.code where recipientcode = ? group by sectorname order by total desc limit 5', [country])

    result_top = len(topsector)
    sectorYearPrep = "SELECT Year, "

    i = 1
    for s in topsector:
        q = "SUM(CASE WHEN sectorcode = %s THEN round(usd_disbursement * 1000000) ELSE 0 END) AS sector" % (s['sectorcode']) 
        sectorYearPrep = sectorYearPrep + q + str(i) 
        if i < result_top:
            sectorYearPrep = sectorYearPrep + ","
        i+=1

    sectorYearPrep = sectorYearPrep + " FROM crs where recipientcode = %s group by Year" % (country)    
        
    sectoryears = query_db(sectorYearPrep)

    disbYears = query_db('select Year as jahr, recipientcode from crs where length(usd_disbursement) > 1 and recipientcode = ? and Year between 2000 and 2012 group by Year', [country])
    
    info = query_db('SELECT count(crsid) as total_activities, recipientname, recipientcode, round(sum(usd_commitment * 1000000)) as total_sum, round(sum(usd_disbursement * 1000000)) as disbursement, countries.land as land FROM crs join countries on countries.code = crs.recipientcode where Year between 2000 and 2012 and recipientcode = ?', [country], one=True)
    info['jahr'] = year
    
    totalYear = query_db('SELECT round(sum(usd_disbursement * 1000000)) as total, recipientcode FROM crs join countries on countries.code = crs.recipientcode where Year = ? and recipientcode = ?', [year, country], one=True)
    total = totalYear['total'] 
	
    flows = query_db('SELECT Year, SUM(CASE WHEN flowcode = 11 THEN usd_disbursement * 1000000 ELSE 0 END) AS grant, SUM(CASE WHEN flowcode = 13 THEN usd_disbursement * 1000000 ELSE 0 END) AS loan FROM crs  where  recipientcode = ? group by Year', [country])		
	
    wb_average = query_db('select indikatoren.average, indikatoren.t2000, indikatoren.t2009, indikatoren.t2010, sectorcode.indicator_name, sectorcode.attribution, sectorcode.short, sectorcode.indicator_name from indikatoren join countries on countries.country_wb = indikatoren.country_name join sectorcode on sectorcode.indicator = indikatoren.series_code  where countries.code = ?  and series_code != "IT.CEL.SETS.P2" and series_code != "IC.LGL.CRED.XQ" order by series_code asc', [country])
	
    human = query_db('SELECT * FROM human join countries on countries.country_un = human.country where code = ?', [country], one=True)
		
    file = open('log.txt', 'a')	
    input = country + ": " + year + "\n\n"
    file.write(input)
    file.close()
		
    entries = []
    for u in query_db('SELECT round(sum(usd_disbursement * 1000000)) as main_value, crsid, sectorname, sectorcode, recipientcode, count(sectorname) as activities, sectorcode.sector_de, Year FROM crs join sectorcode on sectorcode.code = crs.sectorcode where recipientcode = ? and Year = ? group by sectorname order by main_value desc', [country, year]):		
		  u['treearea'] = u['main_value'] / total * 100
		  u = tremapCalc(u)
		  entries.append(u) 
    return render_template('country.html', totalYear=totalYear, wb_average=wb_average, flows=flows, entries=entries, info=info, position=position, human=human, Years=disbYears, sectoryears=sectoryears, topsector=topsector, result_top=result_top)
    #return str(disbYears)
    
@app.route('/sector/<country>/<sector>/')
def show_sektor(country,sector):
    
    activities = query_db('SELECT sectorcode.sector_de as sector_de, Year, sectorcode, count(recipientcode) as total_activities FROM crs join sectorcode on sectorcode.code = crs.sectorcode where Year between 2000 and 2012 and recipientcode = ? and sectorcode = ? group by Year', [country, sector])
    
    totalYear = query_db('SELECT round(sum(usd_commitment * 1000000)) as total, round(sum(usd_disbursement * 1000000)) as disb_total, recipientname, countries.land, sectorname FROM crs join countries on countries.code = crs.recipientcode where Year between 2000 and 2012 and recipientcode = ? and sectorcode = ?', [country, sector], one=True)
    total = totalYear['disb_total']
    
    history = query_db('SELECT round(sum(usd_disbursement * 1000000),2) as main_value, round(sum(usd_disbursement * 1000000),2) as disb_value, Year FROM crs where recipientcode = ? and sectorcode = ? and Year between 2000 and 2012 group by Year order by Year asc', [country, sector])
    
    flows = query_db('SELECT Year, SUM(CASE WHEN flowcode = 11 THEN usd_disbursement * 1000000 ELSE 0 END) AS grant, SUM(CASE WHEN flowcode = 13 THEN usd_disbursement * 1000000 ELSE 0 END) AS loan FROM crs  where  recipientcode = ? and sectorcode = ? group by Year', [country, sector])
    
    entries = query_db('SELECT crsid, round(usd_disbursement * 1000000,2) as main_value, flowname, agencyname, rowid, sectorname, sectorcode, purposename, projecttitle, Year FROM crs where recipientcode = ? and sectorcode = ? and Year between 2000 and 2012 and main_value > 0 order by Year desc', [country, sector])
    
    spitzenreiter = query_db('SELECT round(sum(usd_disbursement * 1000000),2) as total, crsid, sectorname, countries.land as land, recipientname, count(sectorname) as activities FROM crs  join countries on countries.code = crs.recipientcode where sectorcode = ? group by recipientname order by total desc limit 1', [sector], one=True)

    purposes = []
    for u in query_db('SELECT round(sum(usd_disbursement * 1000000),2) as main_value, rowid, sectorname, sectorcode, purposename, Year FROM crs where recipientcode = ? and sectorcode = ? and Year between 2000 and 2012 group by purposename order by Year desc', [country, sector]):
        u['treearea'] = u['main_value'] / total * 100
        u = tremapCalc(u)
        purposes.append(u) 

    return render_template('sector.html', purposes=purposes, entries=entries, flows=flows,activities=activities, history=history, totalYear=totalYear, spitzenreiter=spitzenreiter)

@app.route('/schwerpunkte/')
def show_schwerpunkte():

    total = query_db('SELECT round(sum(usd_disbursement * 1000000),2) as total, crsid, sectorname FROM crs order by total desc', one=True)
    total = total['total']

    entries = []
    for u in query_db('SELECT round(sum(usd_disbursement * 1000000),2) as main_value, crsid, sectorname, sectorcode, count(sectorname) as activities, sectorcode.sector_de FROM crs join sectorcode on sectorcode.code = crs.sectorcode where usd_commitment > 0 group by sectorname order by main_value desc'):		
		u['treearea'] = u['main_value'] / total * 140
		u = tremapCalc(u)
		entries.append(u) 
	
    return render_template('schwerpunkte.html', entries=entries)

@app.route('/schwerpunkt/<schwerpunkt>/')
def show_schwerpunkt(schwerpunkt):

    gesamt = query_db('SELECT round(sum(usd_disbursement * 1000000),2) as total, crsid, sectorname, sectorcode, recipientname, recipientcode, count(sectorname) as activities, sectorcode.sector_de as sector_de FROM crs join sectorcode on sectorcode.code = crs.sectorcode where sectorcode = ? order by total desc', [schwerpunkt], one=True)
    total = gesamt['total']

    entries = []
    for u in query_db('SELECT round(sum(usd_disbursement * 1000000),2) as main_value, crsid, sectorname, sectorcode, recipientname, recipientcode, count(sectorname) as activities, countries.land as land FROM crs join countries on crs.recipientcode = countries.code where sectorcode = ? group by recipientname order by main_value desc', [schwerpunkt]):		
		u['treearea'] = u['main_value'] / total * 170
		u = tremapCalc(u)
		entries.append(u) 
	
    return render_template('schwerpunkt.html', entries=entries, gesamt=gesamt)

@app.route('/organisationen/')
def show_organisationen():
    organisationen = query_db('select code, Organisation, Ort, Quelle, Internet from organisationen where typ is not "check" group by code order by Organisation')

    count_org = query_db('select count(distinct(code)) as count from organisationen')

    sum_euaid = query_db('select sum("Total cost in Euro") as wert from euaid', one=True)
    sum_bmz2010 = query_db('select sum("Wert") as wert from euaid', one=True)
    summe = sum_bmz2010['wert'] + sum_euaid['wert']

    return render_template('organisationen.html', organisationen=organisationen, count_org=count_org, summe=summe)
    
@app.route('/trends/')
def show_trends():
	 
    hitlist = query_db('SELECT count(recipientcode) as total_activities, recipientname, recipientcode, round(sum(usd_disbursement * 1000000)) as total_sum, countries.land as land FROM crs join countries on countries.code = crs.recipientcode where Year between 2000 and 2012 and recipientname not like "%regional%" group by recipientname order by total_sum desc limit 10')
    
    aktuell = query_db('SELECT count(recipientcode) as total_activities, recipientname,recipientcode,round(sum(usd_disbursement * 1000000)) as total_sum, countries.land as land FROM crs join countries on countries.code = crs.recipientcode where Year = 2011 and recipientname not like "%regional%" group by recipientname order by total_sum desc limit 10')
 
    topsector = query_db('select sum(usd_disbursement * 1000000) as total, sectorcode.sector_de as sectorname, crs.sectorcode from crs join sectorcode on crs.sectorcode = sectorcode.code group by sectorname order by total desc limit 5')
    
    sectorYearPrep = 'SELECT Year, SUM(CASE WHEN sectorcode = %s  THEN round(usd_disbursement * 1000000) ELSE 0 END) AS sector1, SUM(CASE WHEN sectorcode = %s THEN round(usd_disbursement * 1000000) ELSE 0 END) AS sector2,SUM(CASE WHEN sectorcode = %s THEN round(usd_disbursement * 1000000) ELSE 0 END) AS sector3,SUM(CASE WHEN sectorcode = %s THEN round(usd_disbursement * 1000000) ELSE 0 END) AS sector4, SUM(CASE WHEN sectorcode = %s THEN round(usd_disbursement * 1000000) ELSE 0 END) AS sector5 FROM crs group by Year' % (topsector[0]['sectorcode'], topsector[1]['sectorcode'], topsector[2]['sectorcode'], topsector[3]['sectorcode'], topsector[4]['sectorcode'])
    
    regions = query_db("SELECT Year, SUM(CASE WHEN regionname = 'Middle East' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't1', SUM(CASE WHEN regionname = 'Europe' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't2', SUM(CASE WHEN regionname = 'Far East Asia' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't3', SUM(CASE WHEN regionname = 'North & Central America' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't4', SUM(CASE WHEN regionname = 'North of Sahara' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't5', SUM(CASE WHEN regionname = 'Oceania' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't6', SUM(CASE WHEN regionname = 'South & Central Asia' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't7', SUM(CASE WHEN regionname = 'South America' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't8', SUM(CASE WHEN regionname = 'South of Sahara' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't9', SUM(CASE WHEN regionname = 'Unspecified' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't10' FROM crs group by Year")

    #continents = query_db("SELECT Year, SUM(CASE WHEN regionname = 'Europe' THEN round(usd_disbursement * 1000000) ELSE 0 END) AS 't1', SUM(CASE WHEN regionname = 'Africa' THEN usd_disbursement ELSE 0 END) AS 't2', SUM(CASE WHEN regionname = 'America' THEN usd_disbursement ELSE 0 END) AS 't3', SUM(CASE WHEN regionname = 'Asia' THEN usd_disbursement ELSE 0 END) AS 't4', SUM(CASE WHEN regionname = 'Oceania' THEN usd_disbursement ELSE 0 END) AS 't5', SUM(CASE WHEN regionname = 'Unspecified' THEN usd_disbursement ELSE 0 END) AS 't6' FROM crs group by Year")
    
    sectoryears = query_db(sectorYearPrep)

    #return str(regions)
    return render_template('trends.html', sectoryears=sectoryears, regions=regions, hitlist=hitlist, topsector=topsector, aktuell=aktuell)

@app.route('/impressum/')
def show_impressum():	
	return render_template('impressum.html')

@app.route('/spenden/')
def show_spenden():	
	return render_template('spenden.html')

@app.route('/ueber/')
def show_ueber():	
	return render_template('ueber.html')
	
@app.route('/analyse/')
def show_analyse():	
  return render_template('analyse.html')

@app.route('/daten/')
def show_daten():	
	return render_template('daten.html')
	
if __name__ == '__main__':
	app.run()
