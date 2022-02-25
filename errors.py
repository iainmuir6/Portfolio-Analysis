#!/usr/bin/env python

"""
    Author: Iain Muir, iam9ez@virginia.edu
    Date:
    Project:
"""

from datetime import datetime
import sys
import os


def get_error_info():
    """

    :return:
    """

    exc_type, exc_obj, exc_tb = sys.exc_info()
    file_name = os.path.split(
        exc_tb.tb_frame.f_code.co_filename
    )[1]
    type_ = str(exc_type)[8:-2]
    line = exc_tb.tb_lineno

    return type_, file_name, line


class Logging:
    @staticmethod
    def write_error_to_log(self):
        with open('run_log.txt', 'a+') as log:
            current_time = str(datetime.today())
            log.write(
                f'{current_time}, {", ".join([self.module, str(self.line_no), self.error, self.message])}\n'
            )

    @staticmethod
    def write_success_to_log(user):
        with open('run_log.txt', 'a+') as log:
            current_time = str(datetime.today())
            log.write(
                f"{current_time}, {user}'s Report: SUCCESS!\n"
            )


class ErrorHandler(Exception, Logging):
    def __init__(self, message, error, module, line_no, user):
        self.message = message
        self.error = error
        self.module = module
        self.line_no = line_no

    def __str__(self):
        if 'OK' not in self.message:
            Logging.write_error_to_log(self)

        return f"{self.module} (Line: {self.line_no}) || {self.error}: {self.message}"
