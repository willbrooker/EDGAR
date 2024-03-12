import pandas as pd, re, netaddr
from bisect import bisect 



ips = pd.read_csv("ip2location.csv")

def lookup_region(ip):
    ip = re.sub("[A-Za-z]", "0", ip)
    ip = int(netaddr.IPAddress(ip))
    idx = bisect(ips["low"], ip) - 1
    return ips.iloc[idx]["region"]


class Filing:
    def __init__(self, html):
        self.dates = [n for n in re.findall(r"(19\d{2}|20\d{2})-\d{2}-\d{2}", html) if n[5:7] and int(n[5:7]) <= 12]
        if re.findall(r"SIC=(\d{3,4})", html):
            self.sic = int(re.findall(r"SIC=(\d{3,4})", html)[0])
        else:
            self.sic = None
        
        self.addresses = []
        
        for a in re.findall(r'<div class="mailer">([\s\S]+?)</div>' , html):
            line = []
            for ln in re.findall(r'span class="mailerAddress">([\s\S]+?)</span>' , a):
                line.append(ln.strip())
            if len(line) > 0:
                st = "\n".join(line)
                self.addresses.append(st)

    
    def state(self):
        
        for n in self.addresses:
            match = re.compile(r'\b([A-Z]{2})\s(\d{5})\b').search(n)
            if match:
                return match.group(1)
        return None