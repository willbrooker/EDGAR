# project: p4
# submitter: webrooker
# partner: none
# hours: 25

import pandas as pd
import re
from flask import Flask, request, jsonify, render_template, abort, make_response, Response
from zipfile import ZipFile, ZIP_DEFLATED
from io import TextIOWrapper, BytesIO, StringIO
import csv,time,edgar_utils
import geopandas as gpd
from shapely.geometry import box

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

df = pd.read_csv("server_log.zip", compression = "zip")
counter = 0
A = 0
B = 0





app = Flask(__name__)
# df = pd.read_csv("main.csv")
visitorDict = {}


@app.route('/')
def home():
    global df
    global counter
    counter += 1
    if counter <= 10:
        if counter % 2 == 0:
            with open("index.html") as f:
                html = f.read()
            return html                                                               
        else:
            with open("page2.html") as f:
                html = f.read()
            return html
    else:
        if B > A:
            with open("page2.html") as f:
                html = f.read()
            return html 
        
    with open("index.html") as f:
        html = f.read()

    return html
        



@app.route('/browse.html')
def browse():
    df = pd.read_csv("server_log.zip", compression = "zip")
    return "<h1>Browse first 500 rows of rows.csv</h1>" + df.iloc[:500].to_html()


@app.route("/browse.json")
def browseJson():
    if request.remote_addr in visitorDict:
        lastrequesttime = visitorDict[request.remote_addr]
        rtime = time.time()
        if rtime - lastrequesttime < 60:
            response = make_response("Too many requests. Please try again later.", 429)
            response.headers["Retry-After"] = f"Retry After {str(rtime-lastrequesttime)} seconds"
            return response
    visitorDict[request.remote_addr] = time.time()
    df = pd.read_csv("server_log.zip", compression = "zip")
    return jsonify(df.iloc[:500].to_dict())





@app.route("/visitors.json")
def visitors():
    return list(visitorDict.keys())







@app.route('/index.html')
def index():
    with open("index.html") as f:
        html = f.read()
    return f"<h1>Links to all pages below</h1> {html[-174:]} <br>"







@app.route("/donate.html")
def donate():
    global A, B
    if request.args.get("from") == "A":
        A += 1 
    else: 
        B += 1
    return "<h1>Donations</h1>"


@app.route("/dashboard.svg")
def dash():
    geodata = gpd.read_file("locations.geojson")
    us_states = gpd.read_file("shapes/cb_2018_us_state_20m.shp")

    fig, ax = plt.subplots()

    codes = []
    for n in pd.Series(geodata["address"]).values:
        zipCodes = re.findall(r"[A-Z]{2}\s(\d{5})", n)
        try:
            if len(zipCodes[0]) != 0:
                codes.append(zipCodes[0])
        except:
                codes.append(None)
    geodata['postal_code'] = codes
    geodata = geodata[~geodata['postal_code'].isnull()]

    if 'postal_code' in geodata.columns:
        geodata['postal_code'] = geodata['postal_code'].astype(int)

    geodata = geodata[geodata["postal_code"] > 25000]
    geodata = geodata[geodata["postal_code"] < 65000]

    boundingBox = box(-95, 25, -60, 50)

    geodata = geodata[geodata.intersects(boundingBox)]
    us_states = us_states[us_states.intersects(boundingBox)].to_crs("EPSG:2022")

    us_states.plot(ax=ax, color = "lightgray", figsize = (5, 5))
    final = geodata.to_crs(us_states.crs)
    final.plot(ax=ax, column = "postal_code", legend = True, cmap = "RdBu")

    ax.set_axis_off()

    fake_file = BytesIO()
    fig.savefig(fake_file, format = "svg")
    plt.savefig('dashboard.svg', format='svg')
    plt.close(fig)

    return Response(fake_file.getvalue(), headers = {"Content-Type": "image/svg+xml"})

@app.route("/analysis.html")
def analysis():
    global df
    
    allFiling = []                               #### Q2 Start
    sicCounterDict = {}
    with ZipFile("docs.zip") as zFile:
        for n in zFile.namelist():
            if "htm" in n:
                with zFile.open(n, "r") as htmlFile:
                    html = htmlFile.read().decode("utf-8")
                    Filing = edgar_utils.Filing(str(html))
                    allFiling.append(Filing)
                    sic = Filing.sic
                    if sic != None:
                        if sic not in sicCounterDict:
                            sicCounterDict[sic] = 0
                        sicCounterDict[sic] += 1
    sicCounterDict = dict(sorted(sicCounterDict.items(), key=lambda item: item[1], reverse=True))
    CounterDictHtml = str(pd.DataFrame(sicCounterDict.values(), sicCounterDict.keys()).head(10).to_dict()[0]) #### Q2 End

    df2 = df[["cik","accession","extention"]]
    #df2['doc'] = df.apply(lambda row: f"{int(row['cik'])}/{row['accession']}/{row['extention']}", axis=1)
    df2.loc[:, 'doc'] = df.apply(lambda row: f"{int(row['cik'])}/{row['accession']}/{row['extention']}", axis=1)
    allsearchable = list(df2["doc"].values)
    finalList = [n for n in allsearchable if "htm" in n]
    
    AddressFilings = []
    with ZipFile("docs.zip") as zFile:
        for n in finalList: 
            try:
                with zFile.open(n, "r") as htmlFile:
                    html = htmlFile.read()
                    Filing = edgar_utils.Filing(str(html))
                    AddressFilings.append(Filing)
            except:
                continue
                
    AddressCountsDict = {}
    for n in AddressFilings:
        if n.addresses == None or n.addresses == '':
            continue
        else:
            for address in n.addresses:
                if "\\n" in address:
                    temp = address.replace("\\n", "")
                if temp not in AddressCountsDict:
                    AddressCountsDict[temp] = 0
                AddressCountsDict[temp] += 1
    AddressCountsDict = dict(sorted(AddressCountsDict.items(), key=lambda item: item[1], reverse=True))
    AddressCountsDict = {k: v for k, v in AddressCountsDict.items() if v >= 300}
    AddressCountsDict = str(pd.DataFrame(AddressCountsDict.values(), AddressCountsDict.keys()).head(12).to_dict()[0])
    
    q1 = str(df["ip"].value_counts().head(10).to_dict())
    q2 = CounterDictHtml
    q3 = AddressCountsDict
    
    return f"""
    <h1>Analysis of EDGAR Web Logs</h1>
    <p>Q1: how many filings have been accessed by the top ten IPs?</p>
    <p>{str(q1)}</p>
    <p>Q2: what is the distribution of SIC codes for the filings in docs.zip?</p>
    <p>{str(q2)}</p>
    <p>Q3: what are the most commonly seen street addresses?</p>
    <p>{str(q3)}</p>
    <h4>Dashboard: geographic plotting of postal code</h4>
    <img src="dashboard.svg">
    """

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, threaded=False) # don't change this line!

# NOTE: app.run never returns (it runs for ever, unless you kill the process)
# Thus, don't define any functions after the app.run call, because it will
# never get that far.