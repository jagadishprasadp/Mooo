import sys

from streamlit.web import cli as stcli
#test 

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "app.py", *sys.argv[1:]]
    raise SystemExit(stcli.main())
