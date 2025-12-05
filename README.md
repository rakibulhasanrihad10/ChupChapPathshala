# library-management-system
A Flask-based library and e-commerce platform.

# how to run
- clone this repo and enter the repo directory
- create and activate python virtual environment
  ``` bash
  virtualenv .venv && source .venv/bin/activate
  ```
- install dependencies
  ``` bash
  pip3 install -r requirements.txt
  ```
- run the dev server
  ``` bash
  flask run --debug
  ```
- open the url printed in the output of flask command

# adding your dependencies
- install your python packages
  ```bash
  pip3 install yourpackages
  ```
- add to requirements.txt
  ```bash
  pip3 freeze > requirements.txt
  ```
