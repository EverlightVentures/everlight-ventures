import React from 'react';
import FeatherIcon from 'react-native-vector-icons/Feather';
import { theme } from '@config/theme';

interface IconProps {
  name: string;
  size?: number;
  color?: string;
}

export const Icon: React.FC<IconProps> = ({
  name,
  size = 24,
  color = theme.colors.white,
}) => {
  return <FeatherIcon name={name} size={size} color={color} />;
};

export default Icon;
