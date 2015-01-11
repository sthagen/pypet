:: Runs a particular test suite
ECHO "------> TESTING <------"
cd ..\..\pypet\tests

IF "%EXAMPLES%"=="ON" (
    ECHO "#### Running the examples #####"
    python run_all_examples.py

    IF ERRORLEVEL 1 (
        ECHO "### Examples failed ###
        EXIT /b 1
    ) ELSE (
        ECHO "### Examples successful ###
    )
)

IF "%MULTIPROC%"=="ON" (
    ECHO "##### Running multiproc tests #####"
    python all_multi_core_tests.py

    IF ERRORLEVEL 1 (
        ECHO "### Multiproc failed ###
        EXIT /b 1
    ) ELSE (
        ECHO "### Multiproc successful ###
    )
)

IF "%MULTIPROC%"=="1" (
    ECHO "##### Running multiproc test suite 1 #####"
    python all_multi_core_tests.py --suite=1

    IF ERRORLEVEL 1 (
        ECHO "### Multiproc failed ###
        EXIT /b 1
    ) ELSE (
        ECHO "### Multiproc successful ###
    )
)

IF "%MULTIPROC%"=="2" (
    ECHO "##### Running multiproc test suite 2 #####"
    python all_multi_core_tests.py --suite=2

    IF ERRORLEVEL 1 (
        ECHO "### Multiproc failed ###
        EXIT /b 1
    ) ELSE (
        ECHO "### Multiproc successful ###
    )
)

IF "%SINGLECORE%"=="ON" (
    ECHO "##### Running all single core tests #####"
    python all_single_core_tests.py

    IF ERRORLEVEL 1 (
        ECHO "### Single core failed ###
        EXIT /b "1
    ) ELSE (
        ECHO "### Single core successful ###
    )
)


