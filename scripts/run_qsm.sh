#!/usr/bin/env bash

bm="$1"
output="$2"
T="$3"
R="$4"
S="$5"

output=$(realpath $output)
instances="${output}/${bm}/${bm}.yaml"
SUMMARY="${output}/summary/${bm}-summary.txt"
echo "==== ${bm} ====" > ${SUMMARY}

SOURCE=${BASH_SOURCE[0]}
while [ -L "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
  SOURCE=$(readlink "$SOURCE")
  [[ $SOURCE != /* ]] && SOURCE=$DIR/$SOURCE
done
DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )

DIRqiQSM="${DIR}/../"
ivybench="${DIRqiQSM}/qiQSM/ic3po/ivybench/"
DIRminimizer="${DIR}/../py-qsm/"
runlim_bin="${DIR}/../runlim-1.10/runlim"


setup_ic3po_env () {
    cd ${DIRqiQSM}
#    source ic3poenv/bin/activate
    cd qiQSM
#    export PYTHONPATH="${PYTHONPATH}:${DIRqiQSM}/qiQSM/ic3po/pysmt/:${DIRqiQSM}/qiQSM/ic3po/repycudd/"
}

echo "1. Generating PLA files"
setup_ic3po_env
python3 ${DIR}/generate_plas.py ${instances} ${ivybench} ${output} ${runlim_bin} ${T} ${R} ${S}

echo "2. Generating PI orbits"
python3 ${DIR}/run_minimizer_pis.py ${DIRminimizer} ${instances} ${ivybench} ${output} ${runlim_bin} ${T} ${R} ${S}

echo "3. Quantifying PI orbits"
setup_ic3po_env
mkdir -p ${output}/tmp # ic3po overwrites the output folder, use a tmp folder here
python3 ${DIR}/quantify_pis.py ${instances} ${ivybench} ${output}/tmp ${output} ${runlim_bin} ${T} ${R} ${S}

# #Copy the relevant output to the instance-specific output folder
find ${output}/tmp -iname "*.txt" -exec sh -c 'filename="${1##*/}"; newpath=$(echo ${1} | sed -e s#\/tmp##g );  newname="${filename%_*}.qpis"; cp "${1}" "${newpath%/*}/${newname}" ' sh_cp {} \;

echo "4. Minimizing (python)"
python3 ${DIR}/run_minimizer_qcost.py  ${DIRminimizer} ${instances} ${ivybench} ${output} ${runlim_bin} ${T} ${R} ${S}

echo "5. Minimization Summary:"
echo "" | tee ${SUMMARY}
python3 -u ${DIR}/runlim_stats.py ${output}/${bm} | tee ${SUMMARY}

echo "" >> ${SUMMARY}
grep '^invariant' ${output}/${bm}/*/min-*.log -B 1 | sed -e 's#/min-#:#g' | cut -d':' -f 2- | cut -d':' -f 2- >> ${SUMMARY}

echo ""
echo "6. Ivy Check:"
echo "" >> ${SUMMARY}
echo "ivycheck results:" >> ${SUMMARY}
retCode=2
for dir in ${output}/${bm}/*/
do
    dir=${dir%*/}
    name=${dir##*/}
    cd ${dir}
    ivyFile=${name}.ivy
    if [[ -f "${ivyFile}" ]]; then
      rFile=${name}_R.ivy
      cp ${ivyFile} ${rFile}
      echo -e "\n\n### QSM: R ###" >> ${rFile}
      if [[ -f "min-${name}.log" ]]; then
        grep '^invariant' min-${name}.log >> ${rFile}
        ivycheckLog=${name}-ivycheck.txt
        ivycheckErr=${name}-ivycheck.err
        ${runlim_bin} --time-limit=${T} --real-time-limit=${R} --space-limit=${S} ivy_check ${rFile} > ${ivycheckLog} 2>${ivycheckErr}
        if grep -qw "OK" ${ivycheckLog}; then
          echo -e "ivycheck ${name}\tPASS" >> ${SUMMARY}
          retCode=0
        else
          echo -e "ivycheck ${name}\tFAIL" >> ${SUMMARY}
        fi
      fi
    fi
    cd ${DIR}
done
if [[ "${retCode}" = "0" ]]; then
  echo "  PASS"
else
  echo "  FAIL"
fi
exit ${retCode}
