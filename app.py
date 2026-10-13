import json
from dataclasses import asdict
import pandas as pd
import plotly.express as px
import streamlit as st
from core import Parameters, simulate, summary

st.set_page_config(page_title='Rocket Flight Lab',page_icon='🚀',layout='wide')
st.title('Rocket Flight Lab')
st.caption('Vertical flight · changing mass · exponential atmosphere · RK4')
dry=st.sidebar.number_input('Dry mass (kg)',0.1,100.0,1.0,0.1)
prop=st.sidebar.number_input('Propellant (kg)',0.0,20.0,0.25,0.05)
thrust=st.sidebar.number_input('Constant thrust (N)',0.0,10000.0,35.0,1.0)
burn=st.sidebar.number_input('Burn time (s)',0.1,60.0,3.0,0.1)
diameter=st.sidebar.number_input('Diameter (m)',0.01,1.0,0.08,0.01)
cd=st.sidebar.slider('Drag coefficient',0.0,2.0,0.5)
duration=st.sidebar.slider('Time limit (s)',10,300,120)
curve_file=st.sidebar.file_uploader('Optional thrust curve CSV: time_s, thrust_n',type='csv')
p=Parameters(dry,prop,thrust,burn,diameter,cd,duration_s=float(duration))
try:
    curve=None
    if curve_file:
        if curve_file.size>1_000_000: raise ValueError('Curve must be smaller than 1 MB.')
        frame=pd.read_csv(curve_file)
        curve=list(frame[['time_s','thrust_n']].apply(pd.to_numeric).itertuples(index=False,name=None))
    rows=simulate(p,curve); data=pd.DataFrame(rows); stats=summary(rows)
except (ValueError,KeyError,TypeError,UnicodeError,pd.errors.ParserError) as exc:
    st.error(str(exc)); st.stop()
cols=st.columns(4)
for col,label,value in zip(cols,['Apogee','Peak speed','Max dynamic pressure','Landing time'],[f'{stats["apogee_m"]:.1f} m',f'{stats["peak_speed_ms"]:.1f} m/s',f'{stats["max_q_pa"]:.0f} Pa',f'{stats["landing_time_s"]:.1f} s' if stats['landed'] else 'Not reached']): col.metric(label,value)
if stats['apogee_m']==0: st.warning('No lift-off occurred with these parameters.')
elif not stats['landed']: st.info('The simulation ended before touchdown. Increase the time limit.')
for field in ['altitude_m','velocity_ms','thrust_n','dynamic_pressure_pa']:
    st.plotly_chart(px.line(data,x='time_s',y=field,template='plotly_dark'),width='stretch')
with st.expander('Assumptions'):
    st.write('One vertical axis; no wind, attitude, recovery system or terrain. Propellant is consumed linearly over the burn regardless of curve shape. Apogee is the highest sampled altitude. Touchdown time is linearly interpolated; impact is not simulated. Ground contact holds the rocket until positive acceleration can lift it. Density uses an 8,500 m scale height; this is an approximation, not a full standard atmosphere.')
st.download_button('Flight CSV',data.to_csv(index=False),'rocket_flight.csv','text/csv')
st.download_button('Experiment JSON',json.dumps(dict(parameters=asdict(p),curve=curve,summary=stats),indent=2),'rocket_experiment.json','application/json')
