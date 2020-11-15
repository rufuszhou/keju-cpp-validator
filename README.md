**OBSOLETE**

# keju-cpp-validator

**功能**  
验证keju中的cpp项目  

**注意**  
因为存在submodule, 克隆这个repo的时候请加上“--recurse-submodules”选项，如下
```
git clone --recurse-submodules https://github.com/rufuszhou/keju-cpp-validator.git
```

**执行**  
```
% ./keju-cpp-validator.py -h
usage: keju-cpp-validator.py [-h] -p PROJECT -q QUESTION

Validate the provided C++ project

optional arguments:
  -h, --help            show this help message and exit
  -p PROJECT, --project PROJECT
                        A C++ project to check
  -q QUESTION, --question QUESTION
                        The cpp question's name
```

**功能及步骤**  

- 读取validation项目中提供的配置及数据；  
- 对project的基本检查（目录是否存在）；  
- 基于seed工程对project的项目文件进行检查，以确认project中有哪些文件改动；
- 编译project（包含cpplint的执行）
- 执行单元测试
- 检查单元测试中的代码覆盖率
- 扩展功能验证，从validation中读取更多输出，比对project的输出是否正确。
