"""Vertical rocket flight with time-varying mass and RK4 integration (SI units)."""
from dataclasses import dataclass, asdict
import math

@dataclass(frozen=True)
class Parameters:
    dry_mass_kg: float = 1.0
    propellant_kg: float = 0.25
    thrust_n: float = 35.0
    burn_s: float = 3.0
    diameter_m: float = 0.08
    drag_coefficient: float = 0.5
    dt_s: float = 0.02
    duration_s: float = 120.0

    def validate(self):
        if not all(math.isfinite(v) for v in asdict(self).values()):
            raise ValueError('All parameters must be finite.')
        if not 0.01 <= self.dry_mass_kg <= 1000 or not 0 <= self.propellant_kg <= 1000:
            raise ValueError('Mass values are outside supported ranges.')
        if not 0 <= self.thrust_n <= 100000 or not 0.01 <= self.burn_s <= 60:
            raise ValueError('Invalid thrust or burn duration.')
        if not 0.001 <= self.diameter_m <= 5 or not 0 <= self.drag_coefficient <= 3:
            raise ValueError('Invalid diameter or drag coefficient.')
        if not 0.005 <= self.dt_s <= 0.1 or not self.dt_s <= self.duration_s <= 300:
            raise ValueError('Timestep or duration outside supported ranges.')

def atmosphere(altitude):
    height = max(0.0, altitude)
    return 1.225*math.exp(-height/8500), 9.80665*(6371000/(6371000+height))**2

def thrust_at(time, parameters, curve=None):
    if time < 0 or time >= parameters.burn_s: return 0.0
    if curve is None: return parameters.thrust_n
    for (ta, fa), (tb, fb) in zip(curve, curve[1:]):
        if ta <= time <= tb: return fa+(fb-fa)*(time-ta)/(tb-ta)
    return 0.0

def validate_curve(curve, burn):
    if len(curve) < 2 or curve[0][0] != 0 or abs(curve[-1][0]-burn) > 1e-9:
        raise ValueError('Thrust curve must start at 0 and end at burn_s.')
    if any(not math.isfinite(v) or v < 0 for pair in curve for v in pair):
        raise ValueError('Curve values must be finite and nonnegative.')
    if any(b[0] <= a[0] for a,b in zip(curve,curve[1:])):
        raise ValueError('Curve times must increase strictly.')

def simulate(parameters=Parameters(), curve=None):
    parameters.validate()
    if curve is not None: validate_curve(curve,parameters.burn_s)
    area = math.pi*(parameters.diameter_m/2)**2
    h = v = 0.0
    rows = []
    def derivative(t, height, velocity):
        mass = parameters.dry_mass_kg+parameters.propellant_kg*max(0,1-t/parameters.burn_s)
        rho,g = atmosphere(height)
        force = thrust_at(t,parameters,curve)-0.5*rho*parameters.drag_coefficient*area*velocity*abs(velocity)-mass*g
        if height <= 0 and velocity <= 0 and force <= 0: return 0.0,0.0
        return velocity, force/mass
    for i in range(math.ceil(parameters.duration_s/parameters.dt_s)+1):
        t=min(i*parameters.dt_s,parameters.duration_s)
        rho,g = atmosphere(h)
        mass=parameters.dry_mass_kg+parameters.propellant_kg*max(0,1-t/parameters.burn_s)
        rows.append(dict(time_s=t,altitude_m=h,velocity_ms=v,mass_kg=mass,
                         thrust_n=thrust_at(t,parameters,curve),dynamic_pressure_pa=0.5*rho*v*v,
                         acceleration_ms2=derivative(t,h,v)[1]))
        if t >= parameters.duration_s: break
        step=min(parameters.dt_s,parameters.duration_s-t)
        # Split at burnout to avoid integrating across the thrust discontinuity.
        segments = [step]
        if t < parameters.burn_s < t+step:
            segments=[parameters.burn_s-t,t+step-parameters.burn_s]
        for segment in segments:
            # Endpoint force at burnout uses the left limit for this segment.
            end=t+segment
            endpoint=math.nextafter(end,t) if abs(end-parameters.burn_s)<1e-10 else end
            a=derivative(t,h,v)
            b=derivative(t+segment/2,h+a[0]*segment/2,v+a[1]*segment/2)
            c=derivative(t+segment/2,h+b[0]*segment/2,v+b[1]*segment/2)
            d=derivative(endpoint,h+c[0]*segment,v+c[1]*segment)
            next_h=h+segment*(a[0]+2*b[0]+2*c[0]+d[0])/6
            next_v=v+segment*(a[1]+2*b[1]+2*c[1]+d[1])/6
            if h > 0 and next_h <= 0:
                fraction=h/(h-next_h)
                rows.append(dict(time_s=t+segment*fraction,altitude_m=0.0,velocity_ms=v+fraction*(next_v-v),mass_kg=parameters.dry_mass_kg+parameters.propellant_kg*max(0,1-(t+segment*fraction)/parameters.burn_s),thrust_n=0.0,dynamic_pressure_pa=0.5*1.225*(v+fraction*(next_v-v))**2,acceleration_ms2=0.0))
                return rows
            h=max(0.0,next_h); v=next_v if next_h>0 else 0.0
            t=end
    return rows

def summary(rows):
    apogee=max(rows,key=lambda r:r['altitude_m'])
    landed=len(rows)>1 and rows[-1]['altitude_m']==0 and apogee['altitude_m']>0
    return dict(apogee_m=apogee['altitude_m'],apogee_time_s=apogee['time_s'],
                peak_speed_ms=max(abs(r['velocity_ms']) for r in rows),
                max_q_pa=max(r['dynamic_pressure_pa'] for r in rows),
                landed=landed,landing_time_s=rows[-1]['time_s'] if landed else None)
