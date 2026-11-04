export type DrivetrainType = 'mecanum'|'tank';
export const isDrivetrain = (type:string):type is DrivetrainType => type==='mecanum'||type==='tank';
