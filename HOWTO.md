- Create your environment for the repository and activate it (virtualenv)

- In `requirements.txt` change (you can omit this step, but in the future you may need to install the package again):
    ```
    - git+https://gitlab.com/cauldronio/cauldron-pool-scheduler.git
    + -e /location/of/cauldron-pool-scheduler
    ```
  This will install the poolsched package and any changed to poolsched will be shown in this environment.

- Install the packages:

    `pip install -r requirements.txt`

- Create an app:

    `python manage.py startapp app_name`

- Move the app inside cauldron_common_apps

    `mv app_name cauldron_common_apps/`

- Install the app in all the projects used (like `cauldron-web` and `cauldron-poolsched-worker`)


