-- Synthetic classified dump for AetherMask testing
CREATE TABLE bases (
  base_id text NOT NULL,
  installation_name text,
  theater text,
  runway_length_m integer,
  personnel_assigned integer,
  clearance_required text
);

COPY bases (base_id, installation_name, theater, runway_length_m, personnel_assigned, clearance_required) FROM stdin;
BASE-01	Camp Ridgeway	INDOPACOM	4000	3514	TS/SCI
BASE-02	Fort Aldergate	EUCOM	3600	916	CONFIDENTIAL
BASE-03	Base Nordhavn	INDOPACOM	2750	690	SECRET
BASE-04	Airbase Kestrel	EUCOM	2400	2889	TS/SCI
BASE-05	Camp Lindholm	INDOPACOM	3050	3209	TS/SCI
\.

CREATE TABLE strike_log (
  mission_id text, target_designation text, threat_level text, sorties_flown integer
);
INSERT INTO strike_log (mission_id, target_designation, threat_level, sorties_flown) VALUES
('MSN-4000', 'Target BASTION', 'HIGH', 8),
('MSN-4001', 'Target IRONGATE', 'LOW', 2),
('MSN-4002', 'Target NORTHPEAK', 'MEDIUM', 4),
('MSN-4003', 'Target SEAWALL', 'HIGH', 6),
('MSN-4004', 'Target SEAWALL', 'HIGH', 8),
('MSN-4005', 'Target SEAWALL', 'MEDIUM', 3),
('MSN-4006', 'Target SEAWALL', 'MEDIUM', 8),
('MSN-4007', 'Target DEEPWELL', 'MEDIUM', 4),
('MSN-4008', 'Target DEEPWELL', 'MEDIUM', 5),
('MSN-4009', 'Target REDLINE', 'MEDIUM', 4),
('MSN-4010', 'Target SEAWALL', 'MEDIUM', 3),
('MSN-4011', 'Target REDLINE', 'MEDIUM', 8),
('MSN-4012', 'Target SEAWALL', 'HIGH', 5),
('MSN-4013', 'Target REDLINE', 'LOW', 8),
('MSN-4014', 'Target REDLINE', 'MEDIUM', 6),
('MSN-4015', 'Target REDLINE', 'HIGH', 3),
('MSN-4016', 'Target DEEPWELL', 'CRITICAL', 5),
('MSN-4017', 'Target IRONGATE', 'MEDIUM', 3),
('MSN-4018', 'Target SEAWALL', 'MEDIUM', 6),
('MSN-4019', 'Target IRONGATE', 'HIGH', 1),
('MSN-4020', 'Target IRONGATE', 'CRITICAL', 6),
('MSN-4021', 'Target SEAWALL', 'HIGH', 3),
('MSN-4022', 'Target SEAWALL', 'LOW', 3),
('MSN-4023', 'Target SEAWALL', 'LOW', 7),
('MSN-4024', 'Target DEEPWELL', 'HIGH', 8),
('MSN-4025', 'Target NORTHPEAK', 'HIGH', 3),
('MSN-4026', 'Target BASTION', 'LOW', 2),
('MSN-4027', 'Target DEEPWELL', 'MEDIUM', 1),
('MSN-4028', 'Target BASTION', 'HIGH', 6),
('MSN-4029', 'Target IRONGATE', 'HIGH', 5),
('MSN-4030', 'Target DEEPWELL', 'HIGH', 6),
('MSN-4031', 'Target IRONGATE', 'CRITICAL', 5),
('MSN-4032', 'Target REDLINE', 'HIGH', 4),
('MSN-4033', 'Target BASTION', 'MEDIUM', 2),
('MSN-4034', 'Target BASTION', 'LOW', 4),
('MSN-4035', 'Target REDLINE', 'CRITICAL', 8),
('MSN-4036', 'Target DEEPWELL', 'MEDIUM', 3),
('MSN-4037', 'Target NORTHPEAK', 'LOW', 8),
('MSN-4038', 'Target SEAWALL', 'HIGH', 4),
('MSN-4039', 'Target NORTHPEAK', 'MEDIUM', 4);
