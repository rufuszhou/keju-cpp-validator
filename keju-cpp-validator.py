#!/usr/bin/python3
# 脚本命令： keju-cpp-validator.py
# 需求描述：
# 1. 输入：
#           keju考生提交的c++工程目录的路径
#           对应的seed工程的路径
# 2. 操作：
#    1）检查比对两个工程，确认考生提交的是一个有效工程
#    2）编译考生的C++工程，给出编译过程及编译结果 （check style的检查应该是编译的一部分）
#    3）运行unit test，得到单元测试的通过率及代码覆盖率
#    4) 读取seed/src下的CMakefile，得到其可执行文件，提供额外的输入作为测试，并比对其输出

import sys
import os
import io
import shutil
import filecmp
import argparse
import shlex
import subprocess
import json
import tempfile

def _run_shell_command(cmd, out_file=sys.stdout, err_file=sys.stderr):
    result = False
    try:
        # shell_cmd = shlex.split(cmd)
        # print(shell_cmd)
        cp = subprocess.run([cmd], shell=True, universal_newlines=True, check=True,
                            stdout=out_file, stderr=err_file)
        print("{} returned = {}.".format(cmd, cp.returncode))
        result = True
    except subprocess.CalledProcessError as e:
        print("Execution failed:", e)
        result = False
    return result


class KejuCppProject:

    def __init__(self, test_project, seed_project):
        # the test project and its seed project
        self.test_project = test_project
        self.seed_project = seed_project
        print(self.test_project)
        print(self.seed_project)
        self.build_folder = None
        self.executable = None
        self.unittest_cmd = None
        self.coverage_cmd = None
        self.coverage_html_cmd = None
        self.ignored_diff_files = []
        self.forbidden_diff_files = []
        self.ignored_missing_files = []
        self.forbidden_missing_files = []
        self.min_line_rate = None
        self.min_func_rate = None
        self.functional_input = None
        self.functional_output = None
        self.unittest_xml_file = None

        self.work_dir = []

    def _pushd(self, new_work_dir) -> bool:
        result = False
        current_dir = os.getcwd()
        print("current working dir: {}".format(current_dir))
        try:
            os.chdir(new_work_dir)
            self.work_dir.append(current_dir)
            print("Current working dir: {}".format(new_work_dir))
            result = True
        except OSError:
            print("Cannot change to working dir: {}".format(new_work_dir))
        return result

    def _popd(self) -> bool:
        previous_dir = self.work_dir.pop()
        print("Current working dir: {}".format(previous_dir))
        os.chdir(previous_dir)
        return True

    def read_validation_configs(self, validation_folder) -> bool:
        if not os.path.exists(validation_folder):
            print("ERROR: {} doesn't exist.".format(validation_folder))
            return False
        ini_file = os.path.join(validation_folder, "validation.json")
        ini_file_handler = open(ini_file, "r")
        if not ini_file_handler:
            print("ERROR: Failed to open {}".format(ini_file))
            return False
        config = json.loads(ini_file_handler.read())
        ini_file_handler.close()
        print(config)

        if "executable" not in config:
            print("ERROR: there is no executable defined in validation project.")
            return False
        else:
            self.executable = config["executable"]
        if "functional_input" not in config:
            print("ERROR: failed to find functional_input")
            return False
        self.functional_input = os.path.join(validation_folder, config["functional_input"])
        if "functional_output" not in config:
            print("ERROR: failed to find functional_output")
            return False
        self.functional_output = os.path.join(validation_folder, config["functional_output"])

        if "build_folder" not in config:
            self.build_folder = "./build/"
        else:
            self.build_folder = config["build_folder"]

        if "unittest_xml_output" not in config:
            self.unittest_xml_file = "./build/test_detail.xml"
        else:
            self.unittest_xml_file = config["unittest_xml_output"]

        if "unittest_cmd" not in config:
            self.unittest_cmd = "make test"
        else:
            self.unittest_cmd = config["unittest_cmd"]
        if "coverage_cmd" not in config:
            self.coverage_cmd = "make unit_test_coverage"
        else:
            self.coverage_cmd = config["coverage_cmd"]
        if "coverage_html_cmd" not in config:
            self.coverage_html_cmd = "make unit_test_coverage_html"
        else:
            self.coverage_html_cmd = config["coverage_html_cmd"]

        if "ignored_different_files" not in config:
            self.ignored_diff_files = []
        else:
            self.ignored_diff_files = config["ignored_different_files"]
        if "forbidden_different_files" not in config:
            self.forbidden_diff_files = []
        else:
            self.forbidden_diff_files = config["forbidden_different_files"]

        if "ignored_missing_files" not in config:
            self.ignored_missing_files = []
        else:
            self.ignored_missing_files = config["ignored_missing_files"]
        if "forbidden_missing_files" not in config:
            self.forbidden_missing_files = []
        else:
            self.forbidden_missing_files = config["forbidden_missing_files"]

        if "coverage_min_line_rate" not in config:
            self.min_line_rate = 100
        else:
            self.min_line_rate = config["coverage_min_line_rate"]
        if "coverage_min_func_rate" not in config:
            self.min_func_rate = 100
        else:
            self.min_func_rate = config["coverage_min_func_rate"]
        return True

    def basic_check(self) -> bool:
        '''
        perform basic checks.
        :return: True or False
        '''
        if not os.path.isdir(self.test_project):
            print("ERROR: %s is not a valid folder!" % self.test_project)
            return False
        if not os.path.isdir(self.seed_project):
            print("ERROR: %s is not a valid folder!" % self.seed_project)
            return False
        return True

    def _collect_folders_differences(self, dcmp, level, diff_files, left_only, right_only):
        for name in dcmp.diff_files:
            # print("DIFF file %s found in %s and %s" % (name,dcmp.left, dcmp.right))
            diff_files.append(level+"/"+name)
        for name in dcmp.left_only:
            # print("ONLY LEFT file %s found in %s" % (name, dcmp.left))
            left_only.append(level+"/"+name)
        for name in dcmp.right_only:
            # print("ONLY RIGHT file %s found in %s" % (name, dcmp.right))
            right_only.append(level+"/"+name)
        for (l, sub_dcmp) in dcmp.subdirs.items():
            self._collect_folders_differences(sub_dcmp, level+"/"+l, diff_files, left_only, right_only)

    def validate_project_against_seed(self) -> bool:
        '''
        compare the project folder structure with the seed project
        to see if they are the same.
        :return: True or False
        '''
        diff_files = []
        test_only = []
        seed_only = []
        dir_cmp = filecmp.dircmp(self.test_project, self.seed_project)
        # print(dir_cmp.report_full_closure())
        self._collect_folders_differences(dir_cmp, ".", diff_files, test_only, seed_only)
        for d in diff_files:
            if d in self.ignored_diff_files:
                diff_files.remove(d)
        for s in seed_only:
            if s in self.ignored_missing_files:
                seed_only.remove(s)

        result = True
        print("INFO: These files are added: " + str(test_only))
        if len(diff_files) != 0:
            print("WARN: these files are not expected to be changed: " + str(diff_files))
            for d in diff_files:
                if d in self.forbidden_diff_files:
                    print("ERROR: {} is forbidden to be changed.".format(d))
                    result = False
        if len(seed_only) != 0:
            print("WARNING: these files are deleted: " + str(seed_only))
            for s in seed_only:
                if s in self.forbidden_missing_files:
                    print("ERROR: {} is forbidden to be deleted.".format(s))
                    result = False
        return result

    def build(self) -> bool:
        '''
        build the project.
        Need to capture the output of the build command and tell cmake output and
        cpp-lint output.
        :return: True or False
        '''
        build_folder = os.path.join(self.test_project, self.build_folder)
        if os.path.isdir(build_folder):
            shutil.rmtree(build_folder)
        os.makedirs(build_folder)
        if not self._pushd(build_folder):
            print("ERROR: fail to change working directory to {}".format(build_folder))
            return False
        if not _run_shell_command("cmake .."):
            print("ERROR: generating Makefile faild.")
            self._popd()
            return False
        if not _run_shell_command("make"):
            print("ERROR: build failed")
            self._popd()
            return False
        self._popd()
        return True

    def _get_application_path(self) -> str:
        '''
        Parse the CMakeList and locate the path to the compiled application.
        :return: path to the compiled application
        '''
        return os.path.join(self.test_project, self.executable)

    def validate_app_with_input(self) -> bool:
        '''
        locate the application, feed it with the input file, then compare the output
        with the expected_output_file
        :return: True or False
        '''
        with io.open(self.functional_input, 'r', encoding='utf8') as gold_input_file, \
             io.open(self.functional_output, 'r', encoding='utf8') as gold_output_file:
            success = 0
            failure = 0
            for line in gold_input_file.readlines():
                temp = tempfile.NamedTemporaryFile(delete=False, mode="w+")
                current_line_file_name = temp.name
                temp.close()
                with io.open(current_line_file_name, 'w', encoding='utf8') as temp:
                    temp.write(line)
                
                temp = tempfile.NamedTemporaryFile(delete=False, mode="w+")
                current_output_file_name = temp.name
                temp.close()

                cmd = self._get_application_path() + ' ' + current_line_file_name

                temp_output = io.open(current_output_file_name, "w", encoding='utf8')
                if not _run_shell_command(cmd, out_file=temp_output):
                    print("ERROR: failed to run {}".format(self.executable))
                    temp_output.close()
                    return False
                temp_output.close()

                gold_output_line = gold_output_file.readline()
                temp_input = io.open(current_output_file_name, "r", encoding='utf8')
                current_output_line = temp_input.readline()
                temp_input.close()

                if gold_output_line != current_output_line:
                    sys.stdout.write(str("ERROR: result of input ({}) is not correct.".format(line).encode('utf8'))+'\n')
                    failure = failure + 1
                else:
                    sys.stdout.write(str("The result with input ({}) is correct.".format(line).encode('utf8'))+'\n')
                    success = success + 1

                os.unlink(current_output_file_name)
                os.unlink(current_line_file_name)

            print("Test result: {}/{} passed.".format(success, success+failure))
            if failure != 0:
                return False
            else:
                return True

    def validate_unittest_result(self) -> bool:
        '''
        locate the unit test executable, execute it and parse the result to see if
        100% passed
        :return: True or False
        '''
        build_folder = os.path.join(self.test_project, self.build_folder)
        os.makedirs(build_folder, exist_ok=True)
        if not self._pushd(build_folder):
            print("ERROR: fail to change working directory to {}".format(build_folder))
            return False
        if not _run_shell_command(self.unittest_cmd):
            print("ERROR: unit test faild.")
            self._popd()
            return False
        self._popd()
        return True

    def validate_unittest_coverage(self) -> bool:
        '''
        locate the unit test executable, execute it and get the coverage rate
        :return: (True or false, True or false)
        '''
        result = False

        build_folder = os.path.join(self.test_project, self.build_folder)
        os.makedirs(build_folder, exist_ok=True)
        if not self._pushd(build_folder):
            print("ERROR: fail to change working directory to {}".format(build_folder))
            return False
        
        if os.path.isfile(self.unittest_xml_file):
            os.unlink(self.unittest_xml_file)

        temp = tempfile.NamedTemporaryFile(delete=False, mode="w+")
        coverage_output_file_name = temp.name
        temp.close()
        coverage_output_file = open(coverage_output_file_name, "w+")
        if not _run_shell_command(self.coverage_cmd, out_file = coverage_output_file):
            print("ERROR: unit test faild.")
            self._popd()
            return False
        coverage_output_file.close()
        with io.open(coverage_output_file_name, 'r', encoding='utf8') as coverage_parse:
            for line in coverage_parse.readlines():
                if line.startswith("TOTAL"):
                    line = line.rstrip()
                    words = line.split(' ')
                    print(words)
                    for w in words:
                        if w.endswith("%"):
                            w = w[0:len(w)-1]
                            coverage_rate = int(w)
                            if coverage_rate >= self.min_line_rate:
                                result = True
                            else:
                                print("Coverage rate is low: {}, the expected rate is >= {}".format(coverage_rate, self.min_line_rate))

        os.unlink(coverage_output_file_name)

        if not os.path.isfile(self.unittest_xml_file):
            print("ERROR: failed to find the unit test xml file.")
            result = False
        os.unlink(self.unittest_xml_file)

        self._popd()
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Validate the provided C++ project')
    parser.add_argument('-p', '--project', required=True, dest='project',
                        help='A C++ project to check')
    parser.add_argument('-s', '--seed', required=True, dest='seed',
                        help='The seed project to compare')
    parser.add_argument('-v', '--validation', required=True, dest="validation",
                        help='validation project to get data and configurations')

    args = parser.parse_args()
    proj = KejuCppProject(args.project, args.seed)

    print("0. Read validation configurations and data")
    if not proj.read_validation_configs(args.validation):
        exit(1)
    print("1. Basic Check... ")
    if not proj.basic_check():
        exit(1)
    print("2. Check the project files...")
    if not proj.validate_project_against_seed():
        exit(1)
    print("3. Build... ")
    if not proj.build():
        exit(1)
    print("4. Unit Test...")
    if not proj.validate_unittest_result():
        exit(1)
    print("5. Check code coverage from unit test...")
    if not proj.validate_unittest_coverage():
        exit(1)
    print("6. Extended input validation...")
    if not proj.validate_app_with_input():
        exit(1)

    print("All passed. Congratulations!")
    exit(0)
