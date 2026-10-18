const DEVICE_NAMES: Record<string, string> = {
  o2_concentrator: 'Oxygen concentrator',
  o2_cylinder: 'Oxygen cylinder',
  ventilator: 'Ventilator',
  apd_cycler: 'Dialysis cycler',
  powered_bed: 'Powered bed',
  suction: 'Suction pump',
};

// The seeder can add device kinds before the UI knows them; show the raw id rather than nothing.
export const deviceName = (device: string) => DEVICE_NAMES[device] ?? device;
