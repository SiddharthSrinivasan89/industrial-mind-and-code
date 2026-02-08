#!/bin/bash
# Industrial Mind & Code - New Experiment Creator

if [ -z "$1" ]; then
    echo ""
    echo "  Industrial Mind & Code"
    echo "  Usage: ./imc-new-experiment.sh <experiment-name>"
    echo "  Example: ./imc-new-experiment.sh ai-driven-smed"
    echo ""
    exit 1
fi

# Auto-detect next experiment number
LAST_NUM=$(ls -d experiments/imc-* 2>/dev/null | sed 's/.*imc-0*//' \
  | sed 's/-.*//' | sort -n | tail -1)
NEXT_NUM=$(printf "%02d" $((${LAST_NUM:-0} + 1)))
EXPERIMENT_DIR="experiments/imc-${NEXT_NUM}-$1"

# Copy template
cp -r templates/imc-experiment-template $EXPERIMENT_DIR

# Update placeholders
cd $EXPERIMENT_DIR
sed -i "s/Experiment ##/Experiment ${NEXT_NUM}/g" src/main.py 2>/dev/null
sed -i "s/imc-experiment-##/imc-${NEXT_NUM}-$1/g" src/main.py 2>/dev/null

echo ""
echo "  ============================================"
echo "  Industrial Mind & Code"
echo "  Experiment ${NEXT_NUM}: $1"
echo "  Created at: ${EXPERIMENT_DIR}"
echo "  ============================================"
echo ""
echo "  Next steps:"
echo "    cd ${EXPERIMENT_DIR}"
echo "    # Edit README.md with your research question"
echo "    # Build your agents in src/agents/"
echo "    python src/main.py"
echo ""
