// Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::types::{HostName, PointName, Port};

use crate::config::ora_sql::Authentication;

#[derive(Debug)]
pub struct Target {
    pub host: HostName,
    pub point: PointName,
    pub port: Port,
    pub auth: Authentication,
}

impl Target {
    pub fn make_connection_string(&self) -> String {
        format!("{}:{}/{}", self.host, self.port, self.point)
    }
}
