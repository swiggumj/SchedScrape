import os
import sys
import numpy as np
import requests
from bs4 import BeautifulSoup
from astropy.table import Table
from astropy.io import ascii
import logging
import pytz
from datetime import datetime,timedelta

aoDictP2780 = {
    "(a)": "A",
    "(b)": "B",
    "(c)": "C",
    "(d)": "D"
}

aoDictP2945 = {
    "(a)": "0030",
    "(b)": "1640",
    "(c)": "1713",
    "(d)": "2043",
    "(e)": "2317",
    "(b)+(c)": "1640/1713",
    "(e)+(a)": "2317/0030"
}    

class Sched:
    """AO Schedule class

    This class contains a schedule of Arecibo Observatory
    sessions, as well as several useful methods for manipulating
    and accessing related scheduling information. For now, this
    class is project-specific (e.g. P2780/P2945).  

    Contents of schedule are stored in an `astropy.table.Table`.

    Parameters
    ----------
    table: astropy.table.Table
        Pertinent information for all the AO observations is stored
        here. More info coming soon...
    other?
    """

    def __init__(
        self,
        table
    ):

        self.Table = table
        self.nRows = len(self.Table)

        self.ProjID = self.Table['Proj'][0]
        self.TranslateSess()
        self.ObsTimesTZ()
        self.GetWikiLines()


    def TranslateSess(self):
        """
        Translates self.Table['Sess'] to descriptive session identifiers
        according to aoDictP2780 and aoDictP2945.
        """

        if '2780' in self.ProjID:
            self.SessID = np.array([aoDictP2780[ss] for ss in self.Table['Sess']])            
        elif '2945' in self.ProjID:
            self.SessID = np.array([aoDictP2945[ss] for ss in self.Table['Sess']])
        else:
            pass

    def ObsTimesTZ(self):
        """
        Calculate session start/end times by timezone, UTC and APR (America/Puerto Rico)
        """

        APR = pytz.timezone("America/Puerto_Rico")
        UTC = pytz.utc

        BlockDates = np.array(
            [APR.localize(datetime.strptime(ds,'%b_%d_%y')) for ds in self.Table['DateStr']]
        )
        self.StartAPR = np.array(
            [bd + timedelta(days=1.0*c,minutes=15.0*r)
            for bd,c,r in zip(BlockDates,self.Table['BegCol'],self.Table['BegRow'])]
        ) 
        self.EndAPR = np.array(
            [bd + timedelta(days=1.0*c,minutes=15.0*r)
            for bd,c,r in zip(BlockDates,self.Table['EndCol'],self.Table['EndRow'])]
        )

        self.StartUTC = np.array([sa.astimezone(UTC) for sa in self.StartAPR])
        self.EndUTC = np.array([ea.astimezone(UTC) for ea in self.EndAPR])

    # Look for consecutive sessions with the same id and merge them
    def merge_sessions(self):
        pass

    # Print lines that can be copied directly to the wiki schedule
    # Maybe it should be a separate function if I'm going to intersperse P2780/P2945
    """For example:
    2020 Jul 12: 21:15 - Jul 13: 06:30: P2780 (Session C): <br> 
    2020 Jul 12: 04:30 - 06:30: P2945 (2317,0030): <br> 
    2020 Jul 12: 02:00 - 03:00: P2945 (2043): <br> 
    2020 Jul 11: 08:45 - 15:30: P2780 (Session D): <br> 
    """    
    def GetWikiLines(self):
        self.WikiLines = []
        for r,(ast,aet) in enumerate(zip(self.StartAPR,self.EndAPR)):
            WikiStart = datetime.strftime(ast,'%Y %b %d: %H:%M')

            # Check for session spanning multiple columns (days)
            if self.Table['BegCol'][r] == self.Table['EndCol'][r]:
                WikiEnd = datetime.strftime(aet,'%H:%M')
            else:
                WikiEnd = datetime.strftime(aet,'%b %d: %H:%M')

            WikiLine = '%s - %s: %s (Session %s): <br>' % (
                WikiStart,WikiEnd,self.ProjID,self.SessID[r]
            )
            self.WikiLines.append(WikiLine)

    def PrintWikiLines(self):
        for wl in self.WikiLines:
            print(wl)


def fix_colnames(table):
    table.rename_column('col1','DateStr')
    table.rename_column('col2','Proj')
    table.rename_column('col6','Sess')
    table.rename_column('col9','StartLST')
    table.rename_column('col10','EndLST')
    table.rename_column('col12','TimeSys')
    table.rename_column('col13','BegCol')
    table.rename_column('col14','EndCol')
    table.rename_column('col15','BegRow')
    table.rename_column('col16','EndRow')
    table.rename_column('col17','Hours')

def scrape_ao_sched(project,year,log_level=logging.INFO):

    proj = project.lower()
    PROJ = project.upper()
    yr = year[-2:]

    # create logger with 'ao_obs_parser'
    logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)])
    logger = logging.getLogger("ao_obs_parser")
    logger.setLevel(log_level)

    link = 'http://www.naic.edu/~arun/cgi-bin/schedrawd.cgi?year=%s&proj=%s' % (yr,proj)
    page = requests.get(link)
    soup = BeautifulSoup(page.content,'html.parser')

    logger.info('Parsing %s...' % (link))
    souptextlines = soup.get_text().split('\n')

    logger.debug("Parsing souptextlines")
    sched_table = ascii.read(souptextlines)[
        'col1','col2','col6','col9','col10','col12','col13','col14','col15','col16','col17'
        ]

    fix_colnames(sched_table)
    so = Sched(sched_table)

    return so


if __name__ == "__main__":

    x = scrape_ao_sched('P2945','2020',logging.INFO)