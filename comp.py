import glob
import matplotlib.gridspec as gs
import matplotlib.pyplot as plt
import matplotlib.ticker as tkr
import os
import pandas as pd
import vicus

# INIT

# create list of report files to compare
# derive list of scenario names for column labels/figure captions
result_files = sorted(glob.glob('scenario_*.xlsx'))
scenario_names = [os.path.basename(rf)
                  .replace('_', ' ')
                  .replace('.xlsx', '')
                  .replace('scenario ', '')
                  for rf in result_files]
# output files basename (without file extension)
output_filename = 'comp'

# find base scenario and put at first position
base_scenario = scenario_names.index('base')
result_files.insert(0, result_files.pop(base_scenario))
scenario_names.insert(0, scenario_names.pop(base_scenario))

costs = []  # total costs by type and scenario
esums = []  # sum of energy produced by scenario

# READ

for rf in result_files:
    with pd.ExcelFile(rf) as xls:
        cost = xls.parse('Costs', has_index_names=True)
        esum = xls.parse('Energy sums')

        # repair broken MultiIndex in the first column
        esum.reset_index(inplace=True)
        esum.fillna(method='ffill', inplace=True)
        esum.set_index(['level_0', 'level_1'], inplace=True)

        costs.append(cost)
        esums.append(esum)

# merge everything into one DataFrame each
costs = pd.concat(costs, axis=1, keys=scenario_names)
esums = pd.concat(esums, axis=1, keys=scenario_names)

# ANALYSE

# drop redundant 'costs' column label
# make index name nicer for plot
# sort/transpose frame
# convert EUR/a to 1e9 EUR/a
costs.columns = costs.columns.droplevel(1)
costs.index.name = 'Cost type'
costs = costs.sort().transpose()
costs = costs / 1e9

# sum up created energy over all locations, but keeping scenarios (level=0)
# make index name 'Commodity' nicer for plot
# drop all unused commodities and sort/transpose
# convert MWh to GWh
esums = esums.loc['Created'].sum(axis=1, level=0)
esums.index.name = 'Commodity'
used_commodities = (esums.sum(axis=1) > 0)
esums = esums[used_commodities].sort().transpose()
esums = esums / 1e3


# PLOT

fig = plt.figure(figsize=(20, 8))
gs = gs.GridSpec(1, 2, width_ratios=[2, 3])

ax0 = plt.subplot(gs[0])
bp0 = costs.plot(ax=ax0, kind='barh', stacked=True)

ax1 = plt.subplot(gs[1])
esums_colors = [vicus.to_color(commodity) for commodity in esums.columns]
bp1 = esums.plot(ax=ax1, kind='barh', stacked=True, color=esums_colors)

# remove scenario names from second plot
ax1.set_yticklabels('')

# make bar plot edges lighter
for bp in [bp0, bp1]:
    for patch in bp.patches:
        patch.set_edgecolor(vicus.to_color('Decoration'))

# set limits and ticks for both axes
for ax in [ax0, ax1]:
    plt.setp(ax.spines.values(), color=vicus.to_color('Decoration'))
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, 'major', color=vicus.to_color('Decoration'),
                  linestyle='dotted')
    ax.xaxis.set_ticks_position('none')
    ax.yaxis.set_ticks_position('none')
    
    # group 1,000,000 with commas
    group_thousands = tkr.FuncFormatter(lambda x, pos: '{:0,d}'.format(int(x)))
    ax.xaxis.set_major_formatter(group_thousands)

    # legend
    lg = ax.legend(frameon=False, loc='upper center',
                   ncol=len(ax.legend().get_texts()),
                   bbox_to_anchor=(0.5, 1.08))
    plt.setp(lg.get_patches(), edgecolor=vicus.to_color('Decoration'),
             linewidth=0.15)

ax0.set_xlabel('Total costs (1e9 EUR/a)')
ax1.set_xlabel('Total energy produced (GWh)')

for ext in ['png', 'pdf']:
    fig.savefig('{}.{}'.format(output_filename, ext),
                bbox_inches='tight')

# REPORT
with pd.ExcelWriter('{}.{}'.format(output_filename, 'xlsx')) as writer:
    costs.to_excel(writer, 'Costs')
    esums.to_excel(writer, 'Energy sums')
