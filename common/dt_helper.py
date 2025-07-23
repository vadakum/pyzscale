

from datetime import datetime
from datetime import timedelta


class DTHelper:

    @staticmethod
    def diff_days(d1: datetime,
                  d2: datetime
                  ) -> int:
        """
        Common Convention for args:
        d1 : more recent or current timestamp
        d2 : older timestamp
        """
        return (d1 - d2).days

    @staticmethod
    def diff_seconds(d1: datetime,
                     d2: datetime
                     ) -> int:
        """
        (d1 - d2)
        d1 : more recent or current timestamp
        d2 : older timestamp
        """
        return int((d1 - d2).total_seconds())

    @staticmethod
    def diff_days_yyyymmdd(d1: str,
                           d2: str
                           ) -> int:
        """
        (d1 - d2)
        d1 : expected format YYYYMMDD 
        d2 : expected format YYYYMMDD
        """
        return (datetime.strptime(d1, '%Y%m%d') -
                datetime.strptime(d2, '%Y%m%d')).days

    @staticmethod
    def diff_days_yyyymmdd_dash(d1: str,
                                d2: str
                                ) -> int:
        """
        (d1 - d2)
        d1 : expected format YYYY-MM-DD 
        d2 : expected format YYYY-MM-DD
        """
        return (datetime.strptime(d1, '%Y-%m-%d') -
                datetime.strptime(d2, '%Y-%m-%d')).days

    @staticmethod
    def prev_ndays_date(ndays: int,
                        ref_date: datetime
                        ) -> datetime:
        return (ref_date - timedelta(days=ndays))

    """
    To string
    we can pass in : datetime.now()
    """
    @staticmethod
    def to_yyyymmdd(d: datetime) -> str:
        return (d.strftime('%Y%m%d'))

    @staticmethod
    def to_yyyy_mm_dd(d: datetime) -> str:
        return (d.strftime('%Y-%m-%d'))

    @staticmethod
    def to_yyyy_mm_dd_hh_mm_ss(d: datetime) -> str:
        return (d.strftime('%Y-%m-%d %H:%M:%S'))

    @staticmethod
    def from_yyyymmdd_to_yyyy_mm_dd(instr: str) -> str:
        return datetime.strptime(instr, '%Y%m%d').strftime('%Y-%m-%d')
    """
    To Datetime
    """
    @staticmethod
    def to_datetime_from_yyyymmdd(yyyymmdd: str):
        return (datetime.strptime(yyyymmdd, '%Y%m%d'))

    @staticmethod
    def to_datetime_from_yyyy_mm_dd_hh_mm_ss(s: str):
        return (datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))

    """
    Validators
    """
    @staticmethod
    def validate_date(date_text: str):
        """
        validate_date (YYYYMMDD)
        Convert to datetime and then format it back and compare with original input
        """
        try:
            if date_text != datetime.strptime(date_text, "%Y%m%d").strftime('%Y%m%d'):
                return False
        except ValueError:
            return False
        return True

    @staticmethod
    def validate_time(time_text: str):
        """
        validate_date (HH:MM:SS)
        Convert to datetime and then format it back and compare with original input
        """
        try:
            if time_text != datetime.strptime(time_text, "%H:%M:%S").strftime('%H:%M:%S'):
                return False
        except ValueError:
            return False
        return True


class DTStartEndTimeManager:
    """
    HH:MM:SS format 
    """

    def __init__(self,
                 start_time,
                 end_time) -> None:
        self.start_time = start_time
        self.end_time = end_time
        if not DTHelper.validate_time(start_time):
            raise ValueError(
                f"invalid start_time format {start_time} expecting HH:MM:SS format")
        if not DTHelper.validate_time(end_time):
            raise ValueError(
                f"invalid end_time format {end_time} expecting HH:MM:SS format")
        self.start_time = datetime.strptime(start_time, "%H:%M:%S")
        self.end_time = datetime.strptime(end_time, "%H:%M:%S")
        if self.end_time < self.start_time:
            raise ValueError(f"end_time cannot be less than start_time")

    def reached_start_time(self, refts: int):
        refdt = datetime.fromtimestamp(refts)
        start_ts = int(datetime(refdt.year, refdt.month, refdt.day,
                                self.start_time.hour, self.start_time.minute, self.start_time.second).timestamp())
        return (refts > start_ts)

    def crossed_end_time(self, refts: int):
        refdt = datetime.fromtimestamp(refts)
        end_ts = int(datetime(refdt.year, refdt.month, refdt.day,
                              self.end_time.hour, self.end_time.minute, self.end_time.second).timestamp())
        return (refts > end_ts)
