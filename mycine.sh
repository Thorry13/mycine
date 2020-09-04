#!/bin/bash
cd /home/remy/Projects/MyCine
case $1 in
    -a | --add)
            if [ $# -eq 4 ] && [ $3 = --dir ]
            then
                    python3 -c "from lib import add_movie;\
                                add_movie('$2', director='$4')"
            else
                    python3 -c "from lib import add_movie;\
                                add_movie('$2')"
            fi;;

    -d | --delete)
            if [ $# -eq 4 ] && [ $3 = --dir ]
            then
                    python3 -c "from lib import delete_movie;\
                                delete_movie('$2', director='$4')"
            else
                    python3 -c "from lib import delete_movie;\
                                delete_movie('$2')"
            fi;;

    -i | --info)
            if [ $# -eq 4 ] && [ $3 = --dir ]
            then
                    python3 -c "from lib import display_info;\
                                display_info('$2', director='$4')"
            else
                    python3 -c "from lib import display_info;\
                                display_info('$2')"
            fi;;

    -l | --list)
            lmax=25
            watched=None
            shift
            while [ $# -ge 1 ]
            do
                case $1 in
                    -w) watched=True
                        if [ $2 -eq 0 ]
                        then
                            watched=False
                        fi
                        shift; shift;;

                    --lmax) lmax=$2
                            shift; shift;;
                esac
            done
            python3 -c "from lib import list_movies;\
                        list_movies(watched=$watched, lmax=$lmax)";;

    -s | --summary)
            shift
            lmax=25
            director=
            options=0
            while [ $# -ge 1 ]
            do
                case $1 in
                    --lmax)
                        lmax=$2
                        shift; shift;;
                    --dir)
                        director=$2
                        options=1
                        shift; shift;;
                esac
            done
            if [ $options -eq 1 ]
            then
                python3 -c "from lib import make_request;\
                                        make_request('select title, watched from movies where directors like \'%$director%\'', lmax=$lmax)"
            else
                python3 -c "from lib import make_request;\
                            make_request('select watched, count(*) from movies group by watched', lmax=$lmax)"
                total=`mycine -l | wc -l`
                let "total = $total-2" # Remove headlines
                echo
                echo "Total : $total"
            fi;;

    -r | --request)
            shift
            lmax=25
            while [ $# -ge 1 ]
            do
                case $1 in
                    --lmax)
                        lmax=$2
                        shift; shift;;
                    *)
                        request=$1
                        shift;;
                esac
            done
            python3 -c "from lib import make_request;\
                        make_request('$request', lmax=$lmax)";;

    -w | --watched)
            dir=None
            watched=1
            shift;
            while [ $# -ge 1 ]
            do
                case $1 in 
                    --dir) dir="'$2'"
                           shift;shift;;
                    0) watched=0
                       shift;;
                    *) movie=$1
                       shift;;
                esac
            done
            python3 -c "from lib import set_watched;\
                        set_watched('$movie', director=$dir, watched=$watched)"
        ;;
esac
cd ..
