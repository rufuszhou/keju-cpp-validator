#!/usr/bin/python3
# 脚本命： keju-cpp-validator.py
# 需求描述：
# 1. 输入：  keju考生提交的c++工程目录的路径
# 2. 操作：
#    1）编译C++工程，给出编译过程及编译结果 （check style的检查应该是编译的一部分）
#    2）运行unit test，得到单元测试的通过率及代码覆盖率
#    3) 读取C++工程中的CMakefile，得到其可执行文件，提供额外的输入作为测试，并比对其输出
# 3. 环境依赖：
#    1） CMake
#    2） gcc
#    3） googletest
#    4） cpp-lint
#    5） lcov

import sys
import logging
import argparse
import parse_cmake


class KejuCppProject:

    def __init__(self, project):
        self.path_to_project = path

    def basic_check(self):
        '''
        perform basic checks.
        1. if the path is accessible
        2. if the path contains a CMake project
        :return: True or False
        '''
        return True

    def validate_project_against_skeleton(self, path_to_skeleton):
        '''
        compare the project folder structure with the skeleton project
        to see if they are the same.
        :param path_to_skeleton: path to the skeleton project
        :return: True or False
        '''
        return True

    def build(self, file_out, file_error):
        '''
        build the project.
        Need to capture the output of the build command and tell cmake output and
        cpp-lint output.
        :param file_out: the file handler for the build output, can be sys.stdout
        :param file_error: the file handler for the build error, can be sys.stderr
        :return: True or False
        '''
        return True

    def get_application_path(self):
        '''
        Parse the CMakeList and locate the path to the compiled application.
        :return: path to the compiled application
        '''
        return ""

    def get_unitest_path(self):
        '''
        Parse the CMakeList and locate the path to the compiled unit test executable.
        :return: path to the compiled unit test executable
        '''
        return ""

    def validate_app_with_input(self, input_file, expected_output_file):
        '''
        locate the application, feed it with the input file, then compare the output
        with the expected_output_file
        :param input_file:  path to the intput file
        :param expected_output_file: path to the file having expected output
        :return: True or False
        '''
        return True

    def validate_unittest_result(self):
        '''
        locate the unit test executable, execute it and parse the result to see if
        100% passed
        :return: True or False
        '''

    def validate_unittest_coverage(self, expected_line_rate=98, exepcted_function_rate=100):
        '''
        locate the unit test executable, execute it and get the coverage rate
        :param expected_line_rate: expected line coverage rate, in percentage
        :param exepcted_function_rate: expected function coverage rate, in percentage
        :return: (True or false, True or false)
        '''
        return (True, True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Validate the provided C++ project')
    subparsers = parser.add_subparsers(help="Commands")
    parser_check = subparsers.add_parser("check", help="Check Project Structure")
    parser_check.add_argument('-s', '--skeleton', nargs=1, required=True,
                              dest='skeleton', help='The skeleton project to compare')
    parser_build = subparsers.add_parser("build", help="Build Project")
    parser_execute = subparsers.add_parser("run", help="Run Project and validate the output")
    parser_execute.add_argument('-i', '--input', nargs=1, required=True,
                                dest="input_path", help='the input file for the compiled application')
    parser_execute.add_argument('-o', '--output', nargs=1, required=True,
                                dest="gold_output_path", help='the expected output')
    parser_unittest = subparsers.add_parser("unittest", help="Run unit test and check the result")
    parser_unittest.add_argument('-l', '--linerate', default=95, dest="min_line_rate",
                                 type=int, help='the expected minimal line coverage rate')
    parser_unittest.add_argument('-f', '--funcrate', default=100, dest="min_func_rate",
                                 type=int, help='the expecrted minimal function coverage rate')
    parser.add_argument('-p', '--project', nargs=1, required=True, dest='project',
                        help='A C++ project to check')

    args = parser.parse_args()



