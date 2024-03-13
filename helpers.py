import pandas as pd
import requests
import datetime

from flask import redirect, session
from functools import wraps
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource, CustomJS, CheckboxGroup, Div
from bokeh.palettes import Category20
from bokeh.layouts import column, row
from bokeh.embed import components

def login_required(f):
    """
    Decorate routes to require login.
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def exchangerate_api(base_currency, supportedCurrencies):
    api_endpoint = f'https://api.exchangerate-api.com/v4/latest/{base_currency}'
    
    response = requests.get(api_endpoint)

    if response.status_code == 200:
        data = response.json()
        api_last_update = datetime.datetime.utcfromtimestamp(data.get('time_last_updated'))
        filtered_rates = {currency: rate for currency, rate in data['rates'].items() if currency in supportedCurrencies.keys()}
        return api_last_update, filtered_rates
    else:
        return None
    

def plot_bokeh(dates, trValues, categories, baseCurrency):
    df = pd.DataFrame(
    {
        "date": dates,
        "value": trValues,
        "category": categories
    }
)
    # Create a new column with the formatted 'year_month'
    df['year_month'] = df['date'].dt.strftime('%Y-%m')

    grouped = df.groupby(['year_month','category'])['value'].sum().reset_index()
    pivot_df = grouped.pivot(index='year_month', columns='category', values='value').reset_index()

    # Fill NaN values with 0
    pivot_df = pivot_df.fillna(0)
    
    categories = pivot_df.columns[1:].tolist()
    dates = pivot_df['year_month'].apply(str).tolist()
    data = {category: pivot_df[category].tolist() for category in categories}
    data['dates'] = dates
    
    plot_height = 700 + len(categories)*10
    p = figure(x_range=dates, height=plot_height,
            toolbar_location="right", tools="hover", tooltips="$name: @$name{int}", width_policy="max")

    highContrastColors = ['#004488', '#DDAA33', '#BB5566']
    color_palette = Category20[len(categories)] if len(categories) > 2 else highContrastColors[0:len(categories)]

    p.vbar_stack(categories, x='dates', width=0.5, source=data, color=color_palette,
                legend_label=categories)


    # Calculate total values and add labels
    data['total'] = pivot_df[categories].sum(axis=1).tolist()

    p.y_range.start = 0
    p.x_range.range_padding = 0.01
    p.xgrid.grid_line_color = None
    p.axis.minor_tick_line_color = None
    p.outline_line_color = None

    p.yaxis.axis_label = f"Expense in {baseCurrency}"
    p.yaxis.axis_label_text_font_size = '1.2em'

    p.xaxis.major_label_standoff = p.yaxis.major_label_standoff = 15
    p.xaxis.axis_label_standoff = p.yaxis.axis_label_standoff = 15
    p.xaxis.major_label_text_font_size = p.yaxis.major_label_text_font_size = '1.2em'



    # Add legend to right side of figure
    p.legend.orientation = "vertical"
    p.legend.location = "left"
    p.legend.ncols = 2
    p.legend.spacing = 10
    p.legend.label_width = 150
    p.add_layout(p.legend[0], 'above')
    p.legend.click_policy="mute"

    # show(p)

    # Create a new column data source for the plot
    source = ColumnDataSource(data)

    # Create a CheckboxGroup widget with options for all months
    all_months_checkbox = CheckboxGroup(labels=['All Months'], active=[0], css_classes=["form-check"], 
                                        styles={'margin-top': '20px', 'margin-left': '40px',  'font-size': '1.2em'})

    # Create a list of CheckboxGroup widgets for each month
    month_checkboxes = CheckboxGroup(labels=dates, active=list(range(len(dates))), css_classes=["form-check"], 
                                     styles={'margin-left': '40px',  'font-size': '1.2em', 'line-height': '1.5em'})


    # Set the month_checkboxes to be initially disabled
    month_checkboxes.disabled = True

    # Create a callback to update the data source based on the selected months
    callback = CustomJS(args=dict(source=source, p=p, all_months_checkbox=all_months_checkbox, month_checkboxes=month_checkboxes), code="""
        var data = source.data;
        
        // Determine if "All Months" is selected
        var allMonthsSelected = all_months_checkbox.active.includes(0);

        // Update individual month checkboxes based on "All Months" selection
        month_checkboxes.disabled = allMonthsSelected;

        // Automatically tick the individual month checkboxes when "All Months" is selected
        if (allMonthsSelected) {
            month_checkboxes.active = Array.from({ length: month_checkboxes.labels.length }, (_, i) => i);
        }

        // Determine the selected months based on checkboxes
        var selected_months = allMonthsSelected ? data.dates : month_checkboxes.active.map(i => month_checkboxes.labels[i]);

        // Update x_range to show only the selected months
        p.x_range.factors = selected_months;

        // Update data source based on the selected months
        for (var category in data) {
            if (category !== 'dates') {
                data[category] = selected_months.map(function(month) {
                    return data[category][data['dates'].indexOf(month)];
                });
            }
        }

        source.change.emit();
    """)

    # Attach the callback to the CheckboxButtonGroup and CheckboxGroup widgets
    all_months_checkbox.js_on_change('active', callback)
    month_checkboxes.js_on_change('active', callback)

    # descriptive text for checkboxes
    description_text = Div(text="<b>Select months for figure:</b>", width=300, height=20, styles={'margin-top': '30px', 'margin-left': '30px',  'font-size': '1.2em'})

    # Create a layout with the legend and the CheckboxButtonGroup and CheckboxGroup widgets
    layout = column(
    p,
    column(description_text,
    all_months_checkbox,
    month_checkboxes), sizing_mode="scale_width"
    
)
    data['colors'] = color_palette

    # Show the plot
    # show(layout)
    # Get Bokeh components (HTML and JavaScript)
    return components(layout), data